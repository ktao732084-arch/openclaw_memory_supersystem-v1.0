#!/usr/bin/env python3
"""
Proactive Executor v1.0 - 主动行动执行器

功能:
- 运行主动行动循环
- 执行主动建议
- 支持异步和同步模式
- 与 OpenClaw Bridge 集成
"""

import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from proactive_engine import ProactiveMemoryEngine, Suggestion


class ProactiveExecutor:
    """主动行动执行器"""

    def __init__(
        self,
        engine: ProactiveMemoryEngine,
        bridge: Optional[Any] = None,
        on_suggestion: Optional[Callable[[Suggestion], None]] = None,
    ):
        self.engine = engine
        self.bridge = bridge
        self.on_suggestion = on_suggestion
        self.action_log: List[Dict] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def run_sync(self, interval_seconds: Optional[int] = None):
        """同步运行主动行动循环"""
        interval = interval_seconds or self.engine.config.get("suggestion_interval_seconds", 60)
        self._running = True
        self._stop_event.clear()

        while self._running and not self._stop_event.is_set():
            try:
                should_act, reason = self.engine.should_proactive_act()

                if should_act:
                    self._execute_proactive_action(reason)

                self.engine.clear_expired_suggestions()

            except Exception as e:
                self._log_error(f"主动行动循环错误: {e}")

            self._stop_event.wait(interval)

    def start_async(self, interval_seconds: Optional[int] = None):
        """启动异步主动行动循环（在后台线程中运行）"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        def run_loop():
            interval = interval_seconds or self.engine.config.get("suggestion_interval_seconds", 60)
            while self._running and not self._stop_event.is_set():
                try:
                    should_act, reason = self.engine.should_proactive_act()

                    if should_act:
                        self._execute_proactive_action(reason)

                    self.engine.clear_expired_suggestions()

                except Exception as e:
                    self._log_error(f"主动行动循环错误: {e}")

                self._stop_event.wait(interval)

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止主动行动循环"""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _execute_proactive_action(self, reason: str):
        """执行主动行动"""
        suggestion = self.engine.get_next_suggestion()

        if not suggestion:
            return

        action_record = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "suggestion": suggestion.content,
            "type": suggestion.type,
            "intent_topic": suggestion.intent_topic,
        }
        self.action_log.append(action_record)

        if self.on_suggestion:
            try:
                self.on_suggestion(suggestion)
            except Exception as e:
                self._log_error(f"回调执行错误: {e}")

        if self.bridge:
            self._send_via_bridge(suggestion)

    def _send_via_bridge(self, suggestion: Suggestion):
        """通过 Bridge 发送建议"""
        try:
            if hasattr(self.bridge, "send_suggestion"):
                self.bridge.send_suggestion(suggestion.to_dict())
            elif hasattr(self.bridge, "send_message"):
                self.bridge.send_message(suggestion.content)
        except Exception as e:
            self._log_error(f"Bridge 发送错误: {e}")

    def _log_error(self, message: str):
        """记录错误"""
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error": message,
        }
        self.action_log.append(error_record)

    def get_action_log(self, limit: int = 50) -> List[Dict]:
        """获取行动日志"""
        return self.action_log[-limit:]

    def clear_action_log(self):
        """清空行动日志"""
        self.action_log.clear()


class ProactiveExecutorAsync:
    """异步主动行动执行器（用于 async 环境）"""

    def __init__(
        self,
        engine: ProactiveMemoryEngine,
        bridge: Optional[Any] = None,
        on_suggestion: Optional[Callable[[Suggestion], None]] = None,
    ):
        self.engine = engine
        self.bridge = bridge
        self.on_suggestion = on_suggestion
        self.action_log: List[Dict] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run(self, interval_seconds: Optional[int] = None):
        """运行异步主动行动循环"""
        interval = interval_seconds or self.engine.config.get("suggestion_interval_seconds", 60)
        self._running = True

        while self._running:
            try:
                should_act, reason = self.engine.should_proactive_act()

                if should_act:
                    await self._execute_proactive_action(reason)

                self.engine.clear_expired_suggestions()

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log_error(f"主动行动循环错误: {e}")
                await asyncio.sleep(interval)

    def start(self, interval_seconds: Optional[int] = None):
        """启动异步任务"""
        if self._running:
            return

        self._task = asyncio.create_task(self.run(interval_seconds))

    async def stop(self):
        """停止异步任务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _execute_proactive_action(self, reason: str):
        """执行主动行动"""
        suggestion = self.engine.get_next_suggestion()

        if not suggestion:
            return

        action_record = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "suggestion": suggestion.content,
            "type": suggestion.type,
            "intent_topic": suggestion.intent_topic,
        }
        self.action_log.append(action_record)

        if self.on_suggestion:
            try:
                if asyncio.iscoroutinefunction(self.on_suggestion):
                    await self.on_suggestion(suggestion)
                else:
                    self.on_suggestion(suggestion)
            except Exception as e:
                self._log_error(f"回调执行错误: {e}")

        if self.bridge:
            await self._send_via_bridge(suggestion)

    async def _send_via_bridge(self, suggestion: Suggestion):
        """通过 Bridge 发送建议"""
        try:
            if hasattr(self.bridge, "send_suggestion"):
                result = self.bridge.send_suggestion(suggestion.to_dict())
                if asyncio.iscoroutine(result):
                    await result
            elif hasattr(self.bridge, "send_message"):
                result = self.bridge.send_message(suggestion.content)
                if asyncio.iscoroutine(result):
                    await result
        except Exception as e:
            self._log_error(f"Bridge 发送错误: {e}")

    def _log_error(self, message: str):
        """记录错误"""
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error": message,
        }
        self.action_log.append(error_record)

    def get_action_log(self, limit: int = 50) -> List[Dict]:
        """获取行动日志"""
        return self.action_log[-limit:]

    def clear_action_log(self):
        """清空行动日志"""
        self.action_log.clear()


class ProactiveSession:
    """主动记忆会话管理器"""

    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        config: Optional[Dict] = None,
        auto_start: bool = False,
    ):
        from proactive_engine import create_engine

        self.engine = create_engine(memory_dir=memory_dir, config=config)
        self.executor: Optional[ProactiveExecutor] = None
        self._suggestion_handlers: List[Callable[[Suggestion], None]] = []

        if auto_start:
            self.start()

    def start(self, interval_seconds: Optional[int] = None):
        """启动主动记忆会话"""
        if self.executor:
            return

        self.executor = ProactiveExecutor(
            engine=self.engine,
            on_suggestion=self._handle_suggestion,
        )
        self.executor.start_async(interval_seconds)

    def stop(self):
        """停止主动记忆会话"""
        if self.executor:
            self.executor.stop()
            self.executor = None

    def process_message(self, message: str, role: str = "user") -> Dict:
        """处理消息"""
        return self.engine.process_message(message, role)

    def add_suggestion_handler(self, handler: Callable[[Suggestion], None]):
        """添加建议处理器"""
        self._suggestion_handlers.append(handler)

    def remove_suggestion_handler(self, handler: Callable[[Suggestion], None]):
        """移除建议处理器"""
        if handler in self._suggestion_handlers:
            self._suggestion_handlers.remove(handler)

    def _handle_suggestion(self, suggestion: Suggestion):
        """处理建议"""
        for handler in self._suggestion_handlers:
            try:
                handler(suggestion)
            except Exception:
                pass

    def get_context(self) -> Dict:
        """获取当前上下文"""
        return self.engine.get_active_context()

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.engine.get_stats()

    def save_state(self):
        """保存状态"""
        self.engine.save_state()

    def load_state(self) -> bool:
        """加载状态"""
        return self.engine.load_state()


def create_session(
    memory_dir: Optional[Path] = None,
    config: Optional[Dict] = None,
    auto_start: bool = False,
) -> ProactiveSession:
    """工厂函数：创建主动记忆会话"""
    return ProactiveSession(
        memory_dir=memory_dir,
        config=config,
        auto_start=auto_start,
    )
