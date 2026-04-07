#!/usr/bin/env python3
"""
Context Sync Auto-Sync Script - 混合模式
自动识别重要Context + 会话总结
"""

import os
import sys
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone

# Windows编码修复
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# 配置
REPO_PATH = Path("D:/Coding/context-sync-data")
BRANCH = "main"
SESSION_START_TIME = None


def run_cmd(cmd, cwd=None):
    """运行shell命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or REPO_PATH,
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_config():
    """读取配置文件"""
    # 尝试多个路径
    possible_paths = [
        REPO_PATH / ".context" / "config.yml",
        Path("D:/Coding/context-sync-data/.context/config.yml"),
        Path("/d/Coding/context-sync-data/.context/config.yml"),
    ]

    for config_path in possible_paths:
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    print(f"[Config] Loaded from: {config_path}")
                    return config or {}
            except Exception as e:
                print(f"[Config] Error loading {config_path}: {e}")
                continue

    print("[Config] No config file found, using defaults")
    return {}


def sync_push():
    """推送本地更改到GitHub"""
    print("[Context Sync] Pushing local changes...")

    success, stdout, _ = run_cmd("git remote")
    if not stdout.strip():
        print("[Context Sync] No remote configured.")
        return False

    run_cmd("git add -A")

    success, stdout, _ = run_cmd("git status --porcelain")
    if not stdout.strip():
        print("[Context Sync] No changes to push.")
        return True

    success, _, stderr = run_cmd('git commit -m "Auto-sync: $(date +%Y-%m-%d-%H:%M:%S)"')
    if not success and "nothing to commit" not in stderr.lower():
        print(f"[Context Sync] Commit failed: {stderr}")
        return False

    success, stdout, stderr = run_cmd(f"git push origin {BRANCH}")
    if success:
        print("[Context Sync] Push successful.")
        return True
    else:
        print(f"[Context Sync] Push failed: {stderr}")
        return False


def sync_pull():
    """从GitHub拉取最新更改"""
    print("[Context Sync] Pulling latest changes...")

    success, stdout, _ = run_cmd("git remote")
    if not stdout.strip():
        print("[Context Sync] No remote configured.")
        return False

    success, stdout, stderr = run_cmd(f"git pull origin {BRANCH}")
    if success:
        print("[Context Sync] Pull successful.")
        return True
    else:
        print(f"[Context Sync] Pull failed: {stderr}")
        return False


def create_context_file(content, context_type="session", tags=None, title=None):
    """创建Context文件（不自动推送）"""
    import yaml
    import uuid
    import hashlib

    context_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    meta = {
        "context_id": context_id,
        "context_type": context_type,
        "version": "1.0.0",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "source": {
            "device_id": hashlib.sha256(os.getenv("USER", "unknown").encode()).hexdigest()[:16],
            "user_id": os.getenv("USER", "unknown"),
            "agent_type": "claude-code",
        },
        "tags": tags or [],
        "metadata": {
            "size_bytes": len(content.encode('utf-8')),
            "checksum": hashlib.sha256(content.encode()).hexdigest()[:16],
        }
    }

    # 确定路径
    if context_type == "session":
        context_dir = REPO_PATH / "sessions" / now.strftime("%Y/%m/%d")
    elif context_type == "memory":
        context_dir = REPO_PATH / "memory" / "user"
    elif context_type == "project":
        context_dir = REPO_PATH / "projects"
    else:
        context_dir = REPO_PATH / "sessions" / now.strftime("%Y/%m/%d")

    context_dir.mkdir(parents=True, exist_ok=True)

    timestamp = now.strftime("%H%M%S")
    safe_title = f"-{title.replace(' ', '-').lower()[:20]}" if title else ""
    filename = f"{timestamp}-{context_id[:8]}{safe_title}.md"
    file_path = context_dir / filename

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("---\n")
        yaml.dump(meta, f, default_flow_style=False, allow_unicode=True)
        f.write("---\n\n")
        if title:
            f.write(f"# {title}\n\n")
        f.write(content)

    return file_path, context_id


def create_context(content, context_type="session", tags=None, title=None, auto_push=False):
    """创建Context，可选择是否推送"""
    file_path, context_id = create_context_file(content, context_type, tags, title)
    print(f"[Context Sync] Created: {file_path.relative_to(REPO_PATH)}")
    print(f"[Context Sync] Context ID: {context_id}")

    if auto_push:
        sync_push()
    else:
        print("[Context Sync] Created locally. Run 'push' to sync.")

    return context_id


def analyze_importance(summary_text=None):
    """
    分析工作重要性
    返回 (confidence, reason, suggested_tags)
    """
    config = get_config()
    heuristic = config.get("hybrid", {}).get("heuristic", {})

    if not heuristic.get("enabled", False):
        return 0.5, "Heuristic disabled", ["session"]

    keywords = heuristic.get("keywords", [])
    min_lines = heuristic.get("min_lines_changed", 30)
    min_files = heuristic.get("min_files_affected", 2)

    confidence = 0.0
    reasons = []
    tags = []

    # 1. 检查关键词
    if summary_text:
        text_lower = summary_text.lower()
        matched_keywords = [k for k in keywords if k.lower() in text_lower]
        if matched_keywords:
            confidence += 0.3
            reasons.append(f"Keywords: {matched_keywords}")
            tags.extend(matched_keywords[:2])

    # 2. 检查git变更
    success, stdout, _ = run_cmd("git diff --stat")
    if success and stdout:
        # 解析变更统计
        lines = stdout.strip().split('\n')
        if len(lines) > 0:
            # 最后一行通常是总计
            last_line = lines[-1]
            # 提取数字
            import re
            numbers = re.findall(r'\d+', last_line)
            if len(numbers) >= 2:
                files_changed = int(numbers[0])
                insertions = int(numbers[1]) if len(numbers) > 1 else 0
                deletions = int(numbers[2]) if len(numbers) > 2 else 0
                total_lines = insertions + deletions

                if files_changed >= min_files:
                    confidence += 0.25
                    reasons.append(f"Files: {files_changed}")
                    tags.append("multi-file")

                if total_lines >= min_lines:
                    confidence += 0.25
                    reasons.append(f"Lines: +{insertions}/-{deletions}")
                    tags.append("substantial")

    # 3. 配置文件类型
    success, stdout, _ = run_cmd("git diff --name-only")
    if success and stdout:
        files = stdout.strip().split('\n')
        critical_patterns = ['.md', 'config', 'README', 'architecture', 'design']
        for f in files:
            for pattern in critical_patterns:
                if pattern in f.lower():
                    confidence += 0.1
                    reasons.append(f"Critical file: {f}")
                    tags.append("config-change")
                    break

    # 4. 去重tags
    tags = list(set(tags))[:3]  # 最多3个tags

    # 默认tag
    if not tags:
        tags = ["session"]

    return min(confidence, 1.0), "; ".join(reasons), tags


def check():
    """
    检查当前工作状态，自动识别是否应该创建Context
    混合模式核心功能
    """
    config = get_config()
    hybrid_config = config.get("hybrid", {})

    if not hybrid_config.get("heuristic", {}).get("enabled", False):
        print("[Context Sync] Heuristic check disabled.")
        return

    print("[Context Sync] Analyzing work importance...")

    # 获取最后commit以来的变更
    success, stdout, _ = run_cmd("git diff --stat HEAD")
    if not success or not stdout.strip():
        print("[Context Sync] No changes since last commit.")
        return

    # 分析重要性
    confidence, reason, tags = analyze_importance()

    print(f"[Context Sync] Importance score: {confidence:.2f}")
    print(f"[Context Sync] Reasons: {reason}")

    threshold = hybrid_config.get("heuristic", {}).get("confidence_threshold", 0.6)
    high_threshold = hybrid_config.get("heuristic", {}).get("high_confidence_threshold", 0.85)
    auto_push_high = hybrid_config.get("heuristic", {}).get("auto_push_high_confidence", True)

    if confidence >= high_threshold and auto_push_high:
        # 高置信度，自动创建并推送
        print("[Context Sync] High confidence detected! Auto-creating context...")
        content = f"## Work Summary\n\n{reason}\n\n## Changes\n```\n{stdout[:500]}\n```"
        create_context(content, "memory", tags, title="Auto-captured work", auto_push=True)

    elif confidence >= threshold:
        # 达到阈值，建议创建
        print("[Context Sync] Suggested: Create context for this work.")
        print(f"[Context Sync] Suggested tags: {', '.join(tags)}")
        print("[Context Sync] Run: auto-sync.py create \"summary\" --type memory --tags " + ",".join(tags))

    else:
        print("[Context Sync] Changes below importance threshold. Skipping.")


def session_summary():
    """
    生成会话总结
    在会话结束时调用
    """
    config = get_config()
    summary_config = config.get("hybrid", {}).get("session_summary", {})

    if not summary_config.get("enabled", True):
        print("[Context Sync] Session summary disabled.")
        return

    print("[Context Sync] Generating session summary...")

    # 获取本次会话的变更（从session开始）
    success, stdout, _ = run_cmd("git diff --stat HEAD")
    if not success:
        success, stdout, _ = run_cmd("git diff --cached --stat")

    file_stats = stdout if success else "N/A"

    # 获取最近的commits
    success, commits, _ = run_cmd("git log --oneline -5")
    recent_commits = commits if success else "N/A"

    # 构建总结内容
    now = datetime.now(timezone.utc)
    duration = "Unknown"
    if SESSION_START_TIME:
        duration_min = (now - SESSION_START_TIME).total_seconds() / 60
        duration = f"{duration_min:.0f} minutes"

    content = f"""## Session Overview

**Duration**: {duration}
**Time**: {now.strftime('%Y-%m-%d %H:%M')}

## File Changes
```
{file_stats}
```

## Recent Commits
```
{recent_commits}
```

## Notes
- Created automatically at session end
- Review and add important decisions above
"""

    # 创建会话总结
    file_path, context_id = create_context_file(
        content,
        "session",
        ["summary", "auto"],
        title=f"Session Summary {now.strftime('%m-%d %H:%M')}"
    )
    print(f"[Context Sync] Session summary created: {file_path.relative_to(REPO_PATH)}")

    # 会话总结自动推送
    if summary_config.get("auto_push", True):
        sync_push()


def suggest_context(user_input=None):
    """
    智能建议：根据当前状态建议是否创建Context
    """
    confidence, reason, tags = analyze_importance(user_input)

    print("\n" + "="*50)
    print("CONTEXT SYNC - Smart Suggestion")
    print("="*50)
    print(f"Importance Score: {confidence:.0%}")
    print(f"Reason: {reason}")
    print(f"Suggested Tags: {', '.join(tags)}")
    print("-"*50)

    if confidence >= 0.85:
        print("Recommendation: STRONG - Auto-create and push")
        print(f"Command: auto-sync.py create \"your summary\" --type memory --tags {','.join(tags)}")
    elif confidence >= 0.6:
        print("Recommendation: MODERATE - Consider creating context")
        print(f"Command: auto-sync.py create \"your summary\" --type memory --tags {','.join(tags)}")
    else:
        print("Recommendation: LOW - Continue working")
        print("Tip: Add keywords like '完成' or 'fix' to increase importance")

    print("="*50 + "\n")

    return confidence, reason, tags


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: auto-sync.py <command> [options]")
        print("")
        print("Commands:")
        print("  create <content> [--type TYPE] [--title TITLE] [--tags TAGS]  Create context")
        print("  push                                                          Push to GitHub")
        print("  pull                                                          Pull from GitHub")
        print("  sync                                                          Pull then push")
        print("  check                                                         Check importance (hybrid)")
        print("  suggest [text]                                                Suggest and create candidate")
        print("  review [--auto]                                               Review candidate memories")
        print("  memory list                                                   List all memories")
        print("  memory stats                                                  Show memory statistics")
        print("  summary                                                       Generate session summary")
        print("  start                                                         Mark session start")
        print("")
        print("v2.0 Memory OS Commands:")
        print("  suggest '描述'                    # 创建候选记忆（非直接memory）")
        print("  review                            # 交互式审核候选")
        print("  review --auto                     # 自动审核高置信度候选")
        print("  memory list                       # 列出语义记忆")
        print("  memory stats                      # Memory统计")
        print("")
        print("Examples:")
        print("  auto-sync.py suggest '完成了登录功能'  # v2: 创建candidate")
        print("  auto-sync.py review                    # 审核candidate")
        print("  auto-sync.py start                     # 开始会话")
        print("  auto-sync.py summary                   # 结束会话，生成summary")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        content = sys.argv[2] if len(sys.argv) > 2 else "No content"
        context_type = "session"
        title = None
        tags = []

        for i, arg in enumerate(sys.argv):
            if arg == "--type" and i + 1 < len(sys.argv):
                context_type = sys.argv[i + 1]
            elif arg == "--title" and i + 1 < len(sys.argv):
                title = sys.argv[i + 1]
            elif arg == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1].split(",")

        create_context(content, context_type, tags, title)

    elif command == "push":
        sync_push()

    elif command == "pull":
        sync_pull()

    elif command == "sync":
        sync_pull()
        sync_push()

    elif command == "check":
        check()

    elif command == "suggest":
        text = sys.argv[2] if len(sys.argv) > 2 else None
        # v2.0: suggest 现在创建 candidate_memory，不是直接 memory
        suggest_context_v2(text)

    elif command == "review":
        auto_mode = "--auto" in sys.argv
        review_candidates(auto_mode)

    elif command == "memory":
        subcommand = sys.argv[2] if len(sys.argv) > 2 else "list"
        if subcommand == "list":
            list_memories()
        elif subcommand == "stats":
            show_memory_stats()
        else:
            print(f"Unknown memory subcommand: {subcommand}")
            print("Use: memory list | memory stats")

    elif command == "summary":
        session_summary()

    elif command == "start":
        global SESSION_START_TIME
        SESSION_START_TIME = datetime.now(timezone.utc)
        print(f"[Context Sync] Session started at {SESSION_START_TIME}")

    else:
        print(f"Unknown command: {command}")
        print("Run 'auto-sync.py' for help.")


# ============================================
# Memory OS v2.0 Functions
# ============================================

def suggest_context_v2(user_input=None):
    """
    v2.0: suggest 不再直接创建 memory，而是创建 candidate_memory
    """
    try:
        # 导入 v2 模块
        sys.path.insert(0, str(Path(__file__).parent))
        from memory_os_v2 import CandidateManager, ReviewManager
    except ImportError as e:
        print(f"[Error] 无法加载 Memory OS v2 模块: {e}")
        print("请确保 memory_os_v2.py 存在于同一目录")
        return

    print("\n" + "="*60)
    print("🧠 Memory OS v2.0 - Smart Suggestion")
    print("="*60)

    # 分析重要性
    confidence, reason, tags = analyze_importance(user_input)

    print(f"Importance Score: {confidence:.0%}")
    print(f"Reason: {reason}")
    print(f"Suggested Tags: {', '.join(tags)}")
    print("-"*60)

    # 根据分析创建 candidate
    if confidence >= 0.6:
        # 确定 candidate 类型
        candidate_type = "memory"
        if user_input:
            if any(kw in user_input.lower() for kw in ["决定", "decide", "选择"]):
                candidate_type = "decision"
            elif any(kw in user_input.lower() for kw in ["喜欢", "偏好", "prefer"]):
                candidate_type = "preference"
            elif any(kw in user_input.lower() for kw in ["原则", "principle", "总是"]):
                candidate_type = "principle"

        # 创建 candidate
        content = user_input if user_input else f"工作记录: {reason}"
        importance = min(10, max(1, int(confidence * 10)))

        manager = CandidateManager()
        candidate = manager.create_candidate(
            content=content,
            candidate_for=candidate_type,
            importance_score=importance,
            confidence_score=confidence,
            extraction_method="rule",
            source_session="current-session"
        )

        print(f"\n✅ 已创建候选记忆 (ID: {candidate.id[:8]})")
        print(f"   类型: {candidate_type}")
        print(f"   重要性: {importance}/10")
        print(f"   置信度: {confidence:.2f}")
        print(f"\n💡 运行 'auto-sync.py review' 进行审核")

    else:
        print("\n⏭️  重要性较低，未创建候选")
        print("   提示: 添加关键词如 '完成' 或 '决定' 可增加重要性")

    print("="*60 + "\n")


def review_candidates(auto_mode=False):
    """
    审核候选记忆
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from memory_os_v2 import ReviewManager
    except ImportError as e:
        print(f"[Error] 无法加载 Memory OS v2 模块: {e}")
        return

    print("\n" + "="*60)
    print("🔍 Memory OS v2.0 - Review Candidates")
    print("="*60)

    manager = ReviewManager()
    approved, rejected = manager.review_candidates(auto_mode=auto_mode)

    # 自动推送
    if approved > 0 or rejected > 0:
        print("\n📤 同步到 GitHub...")
        sync_push()

    print("="*60 + "\n")


def list_memories():
    """
    列出所有语义记忆
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from memory_os_v2 import SemanticMemoryManager
    except ImportError as e:
        print(f"[Error] 无法加载 Memory OS v2 模块: {e}")
        return

    print("\n" + "="*60)
    print("📚 Memory OS v2.0 - Semantic Memories")
    print("="*60)

    manager = SemanticMemoryManager()
    memories = manager.load_all_memories()

    if not memories:
        print("\n  暂无语义记忆")
        print("  运行 'auto-sync.py review' 审核候选")
    else:
        # 按 tier 分组
        by_tier = {}
        for mem in memories:
            tier = mem.memory_tier
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(mem)

        for tier in ["core", "active"]:
            if tier in by_tier:
                print(f"\n[{tier.upper()}]")
                for mem in by_tier[tier][:10]:  # 只显示前10个
                    content_preview = mem.content[:60].replace('\n', ' ')
                    print(f"  • [{mem.context_type:12}] {content_preview}...")

                if len(by_tier[tier]) > 10:
                    print(f"  ... 还有 {len(by_tier[tier]) - 10} 个")

    print(f"\n总计: {len(memories)} 个语义记忆")
    print("="*60 + "\n")


def show_memory_stats():
    """
    显示记忆统计
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from memory_os_v2 import get_memory_stats, CandidateManager
    except ImportError as e:
        print(f"[Error] 无法加载 Memory OS v2 模块: {e}")
        return

    print("\n" + "="*60)
    print("📊 Memory OS v2.0 - Statistics")
    print("="*60)

    # Semantic Memory 统计
    stats = get_memory_stats()
    print("\n[Semantic Memory]")
    print(f"  总计: {stats['total']} 个")
    print(f"  Core: {stats['core_count']} 个")
    print(f"  Active: {stats['active_count']} 个")

    print("\n[按类型]")
    for mem_type, count in sorted(stats['by_type'].items()):
        print(f"  {mem_type:15}: {count:3} 个")

    print("\n[按层级]")
    for tier, count in sorted(stats['by_tier'].items()):
        print(f"  {tier:15}: {count:3} 个")

    # Candidate 统计
    candidate_mgr = CandidateManager()
    pending = candidate_mgr.load_pending_candidates()
    print(f"\n[Candidate Queue]")
    print(f"  待审核: {len(pending)} 个")

    if pending:
        print("\n  运行 'auto-sync.py review' 进行审核")

    print("="*60 + "\n")


# ============================================
# End of Memory OS v2.0 Functions
# ============================================


if __name__ == "__main__":
    main()
