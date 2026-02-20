#!/usr/bin/env python3
"""
OpenClaw Gateway Memory Bridge v1.1
修复：
  - 监听正确的 "agent" 事件（原来监听的 session.message 不存在）
  - 捕获 user 消息改为监听 chat.send 触发的 "chat" 事件
  - 记忆注入改用 chat.inject API（原来的 sessions.patch+systemPromptAppend 字段不存在）
  - sessionKey 从事件中直接取（原来传的是不存在的 sessionId）
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

try:
    import websockets
    from websockets.exceptions import ConnectionClosed

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("Warning: websockets library not installed. Run: pip install websockets")


class ConnectionStatus:
    DISCONNECTED = "disconnected"
    CONNECTING   = "connecting"
    CONNECTED    = "connected"
    RECONNECTING = "reconnecting"


class OpenClawMemoryBridge:
    """OpenClaw Gateway Memory Bridge"""

    def __init__(self, gateway_url="ws://127.0.0.1:18789", gateway_token=None,
                 memory_dir=None, config=None):
        self.gateway_url   = gateway_url
        self.gateway_token = gateway_token or os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
        self.memory_dir    = memory_dir or self._get_memory_dir()
        self.config        = config or self._load_config()

        self.ws     = None
        self.status = ConnectionStatus.DISCONNECTED
        self.running = False

        self._last_injection_time = {}
        self._injection_cooldown  = 10.0   # 同一 session 注入冷却 10s

        self._import_memory_functions()

    # ------------------------------------------------------------------ helpers

    def _get_memory_dir(self):
        workspace = os.environ.get("WORKSPACE", os.getcwd())
        return Path(workspace) / "memory"

    def _load_config(self):
        config_path = self._get_memory_dir() / "config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _import_memory_functions(self):
        scripts_dir = Path(__file__).parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        try:
            from memory import (
                add_to_pending,
                check_urgency,
                cmd_mini_consolidate,
                router_search,
            )
            self.add_to_pending      = add_to_pending
            self.router_search       = router_search
            self.check_urgency       = check_urgency
            self.cmd_mini_consolidate = cmd_mini_consolidate
            self._memory_available   = True
            print("Memory module loaded OK")
        except ImportError as e:
            print(f"Warning: Cannot import memory module: {e}")
            self._memory_available    = False
            self.add_to_pending       = None
            self.router_search        = None
            self.check_urgency        = None
            self.cmd_mini_consolidate = None

    # ------------------------------------------------------------------ connect

    async def connect(self):
        if not WEBSOCKETS_AVAILABLE:
            print("Error: websockets library not available")
            return False

        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            self.status = ConnectionStatus.CONNECTING
            try:
                # 带 token 鉴权
                headers = {}
                if self.gateway_token:
                    headers["Authorization"] = f"Bearer {self.gateway_token}"

                self.ws = await websockets.connect(
                    self.gateway_url,
                    additional_headers=headers,
                    ping_interval=None,   # 已禁用心跳
                    ping_timeout=None,
                    close_timeout=5,
                )
                self.status  = ConnectionStatus.CONNECTED
                self.running = True
                print(f"Connected to OpenClaw Gateway: {self.gateway_url}")
                return True

            except Exception as e:
                self.status = ConnectionStatus.RECONNECTING
                print(f"Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 300)   # 指数退避，最大 5 分钟

        self.status = ConnectionStatus.DISCONNECTED
        print(f"Failed to connect to Gateway: {self.gateway_url}")
        return False

    async def disconnect(self):
        self.running = False
        self.status  = ConnectionStatus.DISCONNECTED
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        print("Disconnected from Gateway")

    # ------------------------------------------------------------------ listen

    async def listen(self):
        if not self.ws:
            return
        try:
            async for raw in self.ws:
                if not self.running:
                    break
                await self._handle_message(raw)
        except ConnectionClosed:
            print("Gateway connection closed")
            self.running = False
            self.status  = ConnectionStatus.DISCONNECTED
        except Exception as e:
            print(f"Message listening error: {e}")
            self.running = False

    async def _handle_message(self, raw_message):
        try:
            msg    = json.loads(raw_message)
            method = msg.get("method", "")
            params = msg.get("params", {})

            # ── 修复1：OpenClaw 广播的是 "agent" 和 "chat" 事件，没有 session.message ──
            if method == "agent":
                await self._on_agent_event(params)
            elif method == "chat":
                await self._on_chat_event(params)
            # 其余事件（tick / health / presence 等）忽略即可

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Message handling error: {e}")

    # ------------------------------------------------------------------ events

    async def _on_agent_event(self, params):
        """
        监听 agent 事件，捕获 assistant 回复文本。
        结构：{ runId, sessionKey, stream, seq, data: { text } }
        stream = "assistant" 时 data.text 是 AI 回复内容。
        """
        stream     = params.get("stream", "")
        session_key = params.get("sessionKey", "")

        if stream != "assistant":
            return

        data    = params.get("data", {})
        content = data.get("text", "")

        if not content or not session_key:
            return

        print(f"[assistant] {session_key[:20]}... | {content[:60]}...")
        await self._capture_and_maybe_inject(session_key, content, role="assistant")

    async def _on_chat_event(self, params):
        """
        监听 chat 事件，捕获 user 发送的消息（state=final 时 message.role=user）。
        结构：{ runId, sessionKey, state, message: { role, content: [{type,text}] } }
        """
        state       = params.get("state", "")
        session_key = params.get("sessionKey", "")
        message     = params.get("message", {})

        if state != "final" or not message or not session_key:
            return

        role = message.get("role", "")
        if role != "user":
            return

        # content 是 [{type: "text", text: "..."}] 数组
        content_blocks = message.get("content", [])
        if isinstance(content_blocks, str):
            content = content_blocks
        else:
            content = " ".join(
                b.get("text", "") for b in content_blocks
                if isinstance(b, dict) and b.get("type") == "text"
            )

        if not content.strip():
            return

        print(f"[user] {session_key[:20]}... | {content[:60]}...")
        await self._capture_and_maybe_inject(session_key, content, role="user")

    # ------------------------------------------------------------------ capture + inject

    async def _capture_and_maybe_inject(self, session_key: str, content: str, role: str):
        """把内容加进 pending，user 消息判断是否需要注入记忆。"""
        if not self._memory_available:
            return

        try:
            source = f"openclaw:{session_key}:{role}"
            record = self.add_to_pending(self.memory_dir, content, source)

            if record:
                if record.get("urgent", False):
                    print(f"Urgent content, triggering mini-consolidate...")
                    await self._trigger_mini_consolidate()

                # 只在 user 消息时检查是否要注入相关记忆
                if role == "user":
                    await self._check_and_inject(session_key, content)

        except Exception as e:
            print(f"Failed to process content: {e}")

    async def _check_and_inject(self, session_key: str, content: str):
        """检测触发词 → 检索记忆 → 注入。"""
        now           = time.time()
        last_injection = self._last_injection_time.get(session_key, 0)
        if now - last_injection < self._injection_cooldown:
            return

        openclaw_cfg = self.config.get("openclaw", {})
        if not openclaw_cfg.get("auto_inject", True):
            return

        trigger_keywords = openclaw_cfg.get(
            "trigger_keywords",
            ["之前", "上次", "以前", "还记得", "我记得", "我喜欢", "我讨厌", "我的", "我们"],
        )

        if not any(kw in content for kw in trigger_keywords):
            return

        if not self.router_search:
            return

        try:
            result = self.router_search(content, self.memory_dir)
            if result and result.get("results"):
                await self._inject_memory(session_key, result)
                self._last_injection_time[session_key] = now
        except Exception as e:
            print(f"Memory search failed: {e}")

    async def _inject_memory(self, session_key: str, search_result: dict):
        """
        修复2：用 chat.inject 注入记忆（原来用的 sessions.patch+systemPromptAppend 不存在）。
        chat.inject 参数：{ sessionKey, message, label? }
        注入结果会以 assistant 消息形式插入会话 transcript。
        """
        if not self.ws:
            return

        memories_text = self._format_memories_for_injection(search_result)
        if not memories_text:
            return

        # ── 修复3：key 字段用 sessionKey 字符串，不是 sessionId UUID ──
        payload = {
            "method": "chat.inject",
            "params": {
                "sessionKey": session_key,
                "message":    memories_text,
                "label":      "🧠 相关记忆",
            },
            "id": f"inject-{int(time.time()*1000)}",
        }

        try:
            await self.ws.send(json.dumps(payload))
            count = len(search_result.get("results", []))
            print(f"Injected {count} memories into {session_key[:20]}...")
        except Exception as e:
            print(f"Injection failed: {e}")

    def _format_memories_for_injection(self, result: dict) -> str:
        results = result.get("results", [])
        if not results:
            return ""

        lines = ["**相关记忆（自动检索）**\n"]
        for r in results[:5]:
            mem_type   = r.get("type", "fact")
            type_tag   = mem_type[0].upper() if mem_type else "F"
            content    = r.get("content", "")[:120]
            confidence = r.get("final_score", r.get("score", 0.5))
            lines.append(f"- [{type_tag}] {content} ({confidence:.0%})")

        return "\n".join(lines)

    # ------------------------------------------------------------------ mini-consolidate

    async def _trigger_mini_consolidate(self):
        if not self._memory_available or not self.cmd_mini_consolidate:
            return

        def run():
            try:
                class Args:
                    pass
                self.cmd_mini_consolidate(Args())
            except Exception as e:
                print(f"Mini-consolidate failed: {e}")

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ run loop

    async def run_forever(self):
        while True:
            connected = await self.connect()
            if connected:
                try:
                    await self.listen()
                except Exception:
                    pass

            print("Reconnecting in 5s...")
            await asyncio.sleep(5)

    async def start(self):
        print("Starting OpenClaw Memory Bridge v1.1")
        print(f"  Gateway : {self.gateway_url}")
        print(f"  Memory  : {self.memory_dir}")
        print(f"  Token   : {'set' if self.gateway_token else 'not set (may fail auth)'}")
        if not self._memory_available:
            print("Warning: Memory module not available, running in listen-only mode")
        await self.run_forever()

    async def stop(self):
        await self.disconnect()


# ------------------------------------------------------------------ CLI

def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Gateway Memory Bridge v1.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--gateway-url",
        default="ws://127.0.0.1:18789",
        help="OpenClaw Gateway WebSocket URL (default: ws://127.0.0.1:18789)",
    )
    parser.add_argument(
        "--gateway-token",
        default=None,
        help="Gateway auth token (or set OPENCLAW_GATEWAY_TOKEN env var)",
    )
    parser.add_argument(
        "--memory-dir",
        default=None,
        help="Memory system directory (default: $WORKSPACE/memory)",
    )
    args = parser.parse_args()

    if not WEBSOCKETS_AVAILABLE:
        print("Error: Please install websockets: pip install websockets")
        sys.exit(1)

    bridge = OpenClawMemoryBridge(
        gateway_url=args.gateway_url,
        gateway_token=args.gateway_token,
        memory_dir=Path(args.memory_dir) if args.memory_dir else None,
    )

    try:
        asyncio.run(bridge.start())
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(bridge.stop())


if __name__ == "__main__":
    main()
