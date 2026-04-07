#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory OS v2.0 - 目录结构初始化
创建三层架构所需的目录结构
"""

import os
import sys
from pathlib import Path

# Windows编码修复
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# 配置路径
REPO_PATH = Path("D:/Coding/context-sync-data")


def create_directory_structure():
    """创建 v2 目录结构"""
    print("=" * 60)
    print("🚀 Memory OS v2.0 - 初始化目录结构")
    print("=" * 60)

    directories = [
        # Logs 层 - 事件流
        "logs/sessions",
        "logs/summaries",
        "logs/milestones",
        "logs/auto",

        # Candidate 层 - 待审核
        "candidate/pending",
        "candidate/approved",
        "candidate/rejected",

        # Memory 层 - Core（必须加载）
        "memory/core/preferences",
        "memory/core/decisions",
        "memory/core/principles",

        # Memory 层 - Active（动态加载）
        "memory/active/facts",
        "memory/active/goals",

        # Memory 层 - Archive（历史归档）
        "memory/archive/preferences",
        "memory/archive/decisions",
        "memory/archive/principles",
        "memory/archive/facts",
        "memory/archive/goals",

        # State 层 - 运行时状态
        ".context/state",
    ]

    created_count = 0
    for dir_path in directories:
        full_path = REPO_PATH / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 创建: {dir_path}")
            created_count += 1
        else:
            print(f"  ⏩ 已存在: {dir_path}")

    # 创建 .gitkeep 文件
    gitkeep_dirs = [
        "logs/sessions",
        "candidate/pending",
    ]
    for dir_path in gitkeep_dirs:
        gitkeep_file = REPO_PATH / dir_path / ".gitkeep"
        if not gitkeep_file.exists():
            gitkeep_file.touch()

    print(f"\n✅ 目录结构初始化完成！")
    print(f"   新创建 {created_count} 个目录")

    return True


def create_v2_config_template():
    """创建 v2 配置模板"""
    config_path = REPO_PATH / ".context" / "config.yml"

    # 检查是否已存在 v2 配置
    if config_path.exists():
        content = config_path.read_text(encoding='utf-8')
        if "memory_os:" in content:
            print("\n⏩ 配置已包含 v2 设置")
            return False

    v2_config = '''
# ============================================
# Memory OS v2.0 Configuration
# ============================================

version: "2.0.0"

# 保留 v1 配置
user:
  id: "Jxy-yxJ"
  email: "your-email@example.com"

sync:
  mode: "hybrid"
  auto_push: false
  auto_pull: true

# ============================================
# Memory OS 核心配置
# ============================================
memory_os:
  enabled: true

  # ----------------------------------------
  # Candidate Memory 配置
  # ----------------------------------------
  candidate:
    auto_extract: true
    min_confidence: 0.6        # 最低置信度 (0-1)
    min_importance: 5          # 最低重要性 (0-10)

    # 自动提取的关键词启发式规则
    heuristic_keywords:
      - "决定"
      - "decide"
      - "偏好"
      - "prefer"
      - "原则"
      - "principle"
      - "总是"
      - "从不"
      - "应该"
      - "使用"
      - "选择"
      - "目标"
      - "goal"

  # ----------------------------------------
  # 审核配置
  # ----------------------------------------
  review:
    mode: "manual"             # "manual" | "auto" | "hybrid"

    # 自动通过阈值
    auto_promote_threshold:
      confidence: 0.9
      importance: 8

    # 需要人工确认
    require_manual_confirm: true

    # 要求提供审核理由
    require_reason: false

  # ----------------------------------------
  # Memory 控制
  # ----------------------------------------
  control:
    # 总数量限制
    max_total: 1000

    # 各类型限制
    max_per_type:
      preference: 100
      decision: 200
      principle: 50
      fact: 500
      goal: 50

    # 去重
    deduplication: true
    similarity_threshold: 0.85

    # 压缩
    compression: true
    compression_threshold: 5    # 5条相似触发压缩

    # 归档
    archive:
      enabled: true
      check_interval_days: 30

  # ----------------------------------------
  # TTL (生存期) 配置
  # ----------------------------------------
  ttl:
    preference: null           # 永久
    decision: 180              # 6个月
    principle: null            # 永久
    fact: 365                  # 1年
    goal: null                 # 达成时归档

    # 低访问自动归档
    auto_archive:
      enabled: true
      min_access_count: 3
      extend_days: 180

  # ----------------------------------------
  # Active Context
  # ----------------------------------------
  active_context:
    enabled: true
    auto_build: true

    # Token 预算
    token_budget:
      max_total: 8000
      memory_allocation: 0.4    # 40% 给 memory
      context_allocation: 0.6   # 60% 给当前上下文

    # Core memory 必须加载
    core_memory_required: true

    # 动态选择策略
    selection_strategy: "recency_relevance"  # "recency" | "relevance" | "recency_relevance"

  # ----------------------------------------
  # 多 Agent 配置
  # ----------------------------------------
  multi_agent:
    enabled: false             # 当前单用户，暂不启用
    mode: "branch"             # "branch" | "direct"
    require_pr: true
    auto_merge_high_confidence: true

# ============================================
# v1 兼容配置
# ============================================
hybrid:
  heuristic:
    enabled: true
    keywords:
      - "complete"
      - "implement"
      - "fix"
      - "refactor"
      - "decide"
      - "resolve"
      - "release"
      - "merge"
      - "finish"
      - "add"
      - "完成"
      - "实现"
      - "修复"
      - "重构"
      - "决策"
      - "解决"
      - "发布"
      - "合并"
    min_lines_changed: 30
    min_files_affected: 2
    min_work_duration_min: 15
    confidence_threshold: 0.6
    auto_push_high_confidence: true
    high_confidence_threshold: 0.85

  session_summary:
    enabled: true
    auto_push: true
    include_file_stats: true
    include_decisions: true

storage:
  provider: "github"
  branch: "main"

security:
  encrypt_sensitive: false
  exclude_patterns:
    - "*.secret"
    - "*password*"
    - "*.env"
'''

    # 如果已有配置，备份并追加
    if config_path.exists():
        backup_path = config_path.with_suffix('.yml.v1-backup')
        config_path.rename(backup_path)
        print(f"\n📦 已备份原配置: {backup_path.name}")

    config_path.write_text(v2_config, encoding='utf-8')
    print("\n✅ 创建 v2 配置文件")

    return True


def main():
    """主函数"""
    if not REPO_PATH.exists():
        print(f"❌ 错误: 仓库路径不存在: {REPO_PATH}")
        print("请检查 CONTEXT_SYNC_REPO 环境变量")
        return 1

    # 1. 创建目录结构
    create_directory_structure()

    # 2. 创建配置
    create_v2_config_template()

    print("\n" + "=" * 60)
    print("🎉 Phase 1 完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 检查配置: cat .context/config.yml")
    print("  2. 开始 Phase 2: 核心流程实现")
    print("  3. 测试: python auto-sync.py suggest '测试'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
