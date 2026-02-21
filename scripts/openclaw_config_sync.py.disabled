#!/usr/bin/env python3
"""
OpenClaw Config Sync Module v1.0
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


class OpenClawConfigSync:
    """OpenClaw Config Synchronizer"""

    DEFAULT_OPENCLAW_CONFIG_NAME = "claw.json"

    def __init__(self, openclaw_config_path=None, memory_dir=None):
        self.memory_dir = memory_dir or self._get_memory_dir()
        self.openclaw_config = openclaw_config_path or self._find_openclaw_config()

    def _get_memory_dir(self):
        """Get memory system directory"""
        workspace = os.environ.get("WORKSPACE", os.getcwd())
        return Path(workspace) / "memory"

    def _find_openclaw_config(self):
        """Find OpenClaw config file"""
        workspace = os.environ.get("WORKSPACE", os.getcwd())

        search_paths = [
            Path(workspace) / self.DEFAULT_OPENCLAW_CONFIG_NAME,
            Path(workspace) / ".claw" / self.DEFAULT_OPENCLAW_CONFIG_NAME,
            Path(workspace) / "config" / self.DEFAULT_OPENCLAW_CONFIG_NAME,
            Path.cwd() / self.DEFAULT_OPENCLAW_CONFIG_NAME,
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_config(self, path):
        """Load config file"""
        if not path.exists():
            return {}

        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_config(self, path, config):
        """Save config file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def sync_layer1_injection(self):
        """
        Sync Layer 1 injection config.
        修复：OpenClaw 没有 systemPromptFiles 字段，
        正确做法是把 snapshot.md 内容追加进 agents.defaults.systemPromptArg，
        或者直接软链 / 写入 AGENTS.md（本实现选后者：追加到 AGENTS.md）。
        """
        if not self.openclaw_config:
            print("Warning: OpenClaw config file not found")
            return False

        snapshot_path = self.memory_dir / "layer1" / "snapshot.md"

        if not snapshot_path.exists():
            print(f"Warning: Layer 1 snapshot not found: {snapshot_path}")
            print("  Run: python3 scripts/memory.py consolidate  to generate it")
            return False

        # 找 workspace 目录（openclaw.json 同级的 workspace/）
        openclaw_dir = Path(self.openclaw_config).parent
        workspace_dir = openclaw_dir / "workspace"
        if not workspace_dir.exists():
            workspace_dir = openclaw_dir  # fallback

        agents_md = workspace_dir / "AGENTS.md"

        MARKER_START = "<!-- memory-system-layer1-start -->"
        MARKER_END   = "<!-- memory-system-layer1-end -->"

        snapshot_content = snapshot_path.read_text(encoding="utf-8").strip()

        new_block = (
            f"\n{MARKER_START}\n"
            f"## 🧠 Memory System Layer 1 (Auto-injected)\n\n"
            f"{snapshot_content}\n"
            f"{MARKER_END}\n"
        )

        if agents_md.exists():
            existing = agents_md.read_text(encoding="utf-8")
            if MARKER_START in existing:
                # 替换已有块
                import re
                updated = re.sub(
                    rf"{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}",
                    new_block.strip(),
                    existing,
                    flags=re.DOTALL,
                )
                agents_md.write_text(updated, encoding="utf-8")
                print(f"Updated Layer 1 block in: {agents_md}")
            else:
                # 追加到末尾
                agents_md.write_text(existing.rstrip() + "\n" + new_block, encoding="utf-8")
                print(f"Appended Layer 1 block to: {agents_md}")
        else:
            agents_md.write_text(f"# AGENTS.md\n{new_block}", encoding="utf-8")
            print(f"Created AGENTS.md with Layer 1 block: {agents_md}")

        return True

    def setup_cron_consolidation(self):
        """Setup cron consolidation"""
        if not self.openclaw_config:
            print("Warning: OpenClaw config file not found")
            return False

        config = self._load_config(self.openclaw_config)

        if "cron" not in config:
            config["cron"] = []

        consolidation_job = {
            "name": "Memory Consolidation",
            "schedule": {"kind": "cron", "expr": "0 3 * * *"},
            "payload": {
                "kind": "systemEvent",
                "text": "Execute memory consolidation: python3 scripts/memory.py consolidate",
            },
            "sessionTarget": "main",
        }

        existing = any(job.get("name") == "Memory Consolidation" for job in config["cron"])

        if not existing:
            config["cron"].append(consolidation_job)
            self._save_config(self.openclaw_config, config)
            print("Configured cron consolidation (daily at 03:00)")
        else:
            print("Cron consolidation already configured")

        return True

    def setup_bridge_autostart(self):
        """Setup bridge autostart"""
        if not self.openclaw_config:
            print("Warning: OpenClaw config file not found")
            return False

        config = self._load_config(self.openclaw_config)

        if "metadata" not in config:
            config["metadata"] = {}
        if "clawdbot" not in config["metadata"]:
            config["metadata"]["clawdbot"] = {}

        bridge_command = "python3 scripts/openclaw_bridge.py"

        if "startCommand" not in config["metadata"]["clawdbot"]:
            config["metadata"]["clawdbot"]["startCommand"] = bridge_command
            self._save_config(self.openclaw_config, config)
            print(f"Configured bridge autostart: {bridge_command}")
        else:
            print("Bridge start command already configured")

        return True

    def validate_config(self):
        """Validate config"""
        results = {"valid": True, "issues": [], "recommendations": []}

        if not self.openclaw_config:
            results["valid"] = False
            results["issues"].append("OpenClaw config file not found")
            return results

        snapshot_path = self.memory_dir / "layer1" / "snapshot.md"
        if not snapshot_path.exists():
            results["issues"].append(f"Layer 1 snapshot not found: {snapshot_path}")
            results["recommendations"].append("Run memory.py consolidate to generate snapshot")

        # 检查 AGENTS.md 是否包含 Layer1 注入块
        openclaw_dir  = Path(self.openclaw_config).parent
        workspace_dir = openclaw_dir / "workspace"
        if not workspace_dir.exists():
            workspace_dir = openclaw_dir
        agents_md = workspace_dir / "AGENTS.md"

        MARKER = "<!-- memory-system-layer1-start -->"
        if not agents_md.exists() or MARKER not in agents_md.read_text(encoding="utf-8"):
            results["issues"].append("Layer 1 not injected into AGENTS.md")
            results["recommendations"].append("Run openclaw_config_sync.py sync-layer1")

        # 检查 cron 是否配置
        config = self._load_config(self.openclaw_config)
        cron_jobs = config.get("cron", [])
        has_consolidation = any(job.get("name") == "Memory Consolidation" for job in cron_jobs)
        if not has_consolidation:
            results["issues"].append("Cron consolidation not configured")
            results["recommendations"].append("Run openclaw_config_sync.py setup-cron")

        if results["issues"]:
            results["valid"] = False

        return results

    def full_sync(self):
        """Full sync"""
        print("Starting full config sync...")
        print(f"   OpenClaw config: {self.openclaw_config}")
        print(f"   Memory dir: {self.memory_dir}")
        print()

        success = True

        print("1. Syncing Layer 1 injection...")
        if not self.sync_layer1_injection():
            success = False
        print()

        print("2. Setting up cron consolidation...")
        if not self.setup_cron_consolidation():
            success = False
        print()

        print("3. Setting up bridge autostart...")
        if not self.setup_bridge_autostart():
            success = False
        print()

        print("4. Validating config...")
        validation = self.validate_config()
        if validation["valid"]:
            print("Config validation passed")
        else:
            print("Config has issues:")
            for issue in validation["issues"]:
                print(f"   - {issue}")
            for rec in validation["recommendations"]:
                print(f"   Hint: {rec}")

        print()

        if success and validation["valid"]:
            print("Full config sync completed successfully!")
        else:
            print("Some config sync steps failed, check above issues")

        return success and validation["valid"]

    def show_status(self):
        """Show current status"""
        print("OpenClaw Integration Status")
        print("=" * 50)
        print(f"OpenClaw config: {self.openclaw_config or 'Not found'}")
        print(f"Memory dir: {self.memory_dir}")
        print()

        snapshot_path = self.memory_dir / "layer1" / "snapshot.md"
        print(f"Layer 1 snapshot: {'Exists' if snapshot_path.exists() else 'Not found'}")

        # 检查 AGENTS.md 注入状态
        if self.openclaw_config:
            openclaw_dir  = Path(self.openclaw_config).parent
            workspace_dir = openclaw_dir / "workspace"
            if not workspace_dir.exists():
                workspace_dir = openclaw_dir
            agents_md = workspace_dir / "AGENTS.md"
            MARKER = "<!-- memory-system-layer1-start -->"
            injected = agents_md.exists() and MARKER in agents_md.read_text(encoding="utf-8")
            print(f"Layer 1 in AGENTS.md: {'Injected' if injected else 'Not injected'}")

            config    = self._load_config(self.openclaw_config)
            cron_jobs = config.get("cron", [])
            has_consolidation = any(job.get("name") == "Memory Consolidation" for job in cron_jobs)
            print(f"Cron consolidation: {'Configured' if has_consolidation else 'Not configured'}")

        print()
        validation = self.validate_config()
        if validation["valid"]:
            print("Status: Fully configured ✅")
        else:
            print("Status: Needs configuration ⚠️")
            for issue in validation["issues"]:
                print(f"  - {issue}")
            for rec in validation["recommendations"]:
                print(f"  → {rec}")


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Config Sync Tool", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--openclaw-config", default=None, help="OpenClaw config file path")

    parser.add_argument("--memory-dir", default=None, help="Memory system directory")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("sync-layer1", help="Sync Layer 1 injection config")
    subparsers.add_parser("setup-cron", help="Setup cron consolidation")
    subparsers.add_parser("setup-bridge", help="Setup bridge autostart")
    subparsers.add_parser("validate", help="Validate config")
    subparsers.add_parser("full-sync", help="Full config sync")
    subparsers.add_parser("status", help="Show current status")

    args = parser.parse_args()

    openclaw_config = Path(args.openclaw_config) if args.openclaw_config else None
    memory_dir = Path(args.memory_dir) if args.memory_dir else None

    sync = OpenClawConfigSync(openclaw_config_path=openclaw_config, memory_dir=memory_dir)

    if args.command == "sync-layer1":
        sync.sync_layer1_injection()
    elif args.command == "setup-cron":
        sync.setup_cron_consolidation()
    elif args.command == "setup-bridge":
        sync.setup_bridge_autostart()
    elif args.command == "validate":
        validation = sync.validate_config()
        if validation["valid"]:
            print("Config validation passed")
        else:
            print("Config has issues:")
            for issue in validation["issues"]:
                print(f"   - {issue}")
            for rec in validation["recommendations"]:
                print(f"   Hint: {rec}")
    elif args.command == "full-sync":
        sync.full_sync()
    elif args.command == "status":
        sync.show_status()
    else:
        sync.show_status()
        print()
        print("Available commands:")
        print("  sync-layer1  - Sync Layer 1 injection config")
        print("  setup-cron   - Setup cron consolidation")
        print("  setup-bridge - Setup bridge autostart")
        print("  validate     - Validate config")
        print("  full-sync    - Full config sync")
        print("  status       - Show current status")


if __name__ == "__main__":
    main()
