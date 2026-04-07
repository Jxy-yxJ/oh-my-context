#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory OS v2.0 - Core Module
核心逻辑：candidate memory、review、promote、memory management
"""

import os
import sys
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher

# Windows编码修复（只在交互式运行时）
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    except:
        pass

# 路径配置
REPO_PATH = Path("D:/Coding/context-sync-data")
CONTEXT_SYNC_PATH = Path("D:/Coding/context-sync-system")


@dataclass
class CandidateMemory:
    """候选记忆数据结构"""
    id: str
    content: str
    candidate_for: str  # "preference" | "decision" | "principle" | "fact"
    importance_score: float  # 0-10
    confidence_score: float  # 0-1
    extraction_method: str  # "ai" | "rule"
    source_session: str
    proposed_at: str
    review_status: str = "pending"  # "pending" | "approved" | "rejected"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    user_feedback: Optional[str] = None


@dataclass
class SemanticMemory:
    """语义记忆数据结构"""
    id: str
    context_type: str  # "preference" | "decision" | "principle" | "fact" | "goal"
    content: str
    memory_tier: str  # "core" | "active" | "archived"
    created_at: str
    updated_at: str
    ttl_days: Optional[int] = None
    access_count: int = 0
    last_accessed: Optional[str] = None
    confidence: float = 0.0
    verified_by: str = "user"
    verified_at: Optional[str] = None
    replaces: List[str] = None
    version: int = 1


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.config_path = REPO_PATH / ".context" / "config.yml"
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置"""
        try:
            import yaml
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[Config] 加载失败: {e}")
        return {}

    def get(self, key: str, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value


class CandidateManager:
    """候选记忆管理器"""

    def __init__(self):
        self.pending_dir = REPO_PATH / "candidate" / "pending"
        self.approved_dir = REPO_PATH / "candidate" / "approved"
        self.rejected_dir = REPO_PATH / "candidate" / "rejected"

    def create_candidate(
        self,
        content: str,
        candidate_for: str,
        importance_score: float,
        confidence_score: float,
        extraction_method: str = "rule",
        source_session: str = ""
    ) -> CandidateMemory:
        """创建候选记忆"""

        candidate = CandidateMemory(
            id=str(uuid.uuid4()),
            content=content,
            candidate_for=candidate_for,
            importance_score=importance_score,
            confidence_score=confidence_score,
            extraction_method=extraction_method,
            source_session=source_session,
            proposed_at=datetime.now(timezone.utc).isoformat()
        )

        # 保存到文件
        self._save_candidate(candidate)

        return candidate

    def _save_candidate(self, candidate: CandidateMemory):
        """保存候选到文件"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"candidate-{timestamp}-{candidate.id[:8]}.md"
        filepath = self.pending_dir / filename

        yaml_content = f"""---
context_id: "{candidate.id}"
context_type: "candidate_memory"
candidate_for: "{candidate.candidate_for}"
importance_score: {candidate.importance_score}
confidence_score: {candidate.confidence_score:.2f}
extraction_method: "{candidate.extraction_method}"
source_session: "{candidate.source_session}"
proposed_at: "{candidate.proposed_at}"
review_status: "{candidate.review_status}"
---

{candidate.content}
"""

        filepath.write_text(yaml_content, encoding='utf-8')
        print(f"  📝 候选: {filename} (importance: {candidate.importance_score}, confidence: {candidate.confidence_score:.2f})")

    def load_pending_candidates(self) -> List[CandidateMemory]:
        """加载所有待审核候选"""
        candidates = []

        if not self.pending_dir.exists():
            return candidates

        for file_path in self.pending_dir.glob("*.md"):
            candidate = self._parse_candidate_file(file_path)
            if candidate and candidate.review_status == "pending":
                candidates.append(candidate)

        # 按重要性排序
        candidates.sort(key=lambda c: c.importance_score, reverse=True)
        return candidates

    def _parse_candidate_file(self, file_path: Path) -> Optional[CandidateMemory]:
        """解析候选文件"""
        try:
            content = file_path.read_text(encoding='utf-8')

            # 解析 frontmatter
            if not content.startswith('---'):
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                return None

            import yaml
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()

            return CandidateMemory(
                id=frontmatter.get('context_id', ''),
                content=body,
                candidate_for=frontmatter.get('candidate_for', 'memory'),
                importance_score=frontmatter.get('importance_score', 0),
                confidence_score=frontmatter.get('confidence_score', 0),
                extraction_method=frontmatter.get('extraction_method', 'rule'),
                source_session=frontmatter.get('source_session', ''),
                proposed_at=frontmatter.get('proposed_at', ''),
                review_status=frontmatter.get('review_status', 'pending'),
                reviewed_by=frontmatter.get('reviewed_by'),
                reviewed_at=frontmatter.get('reviewed_at'),
                user_feedback=frontmatter.get('user_feedback')
            )
        except Exception as e:
            print(f"  ⚠️  解析失败 {file_path.name}: {e}")
            return None

    def archive_candidate(self, candidate: CandidateMemory, status: str, feedback: str = None):
        """归档候选"""
        # 找到原文件
        source_file = None
        for f in self.pending_dir.glob(f"candidate-*-{candidate.id[:8]}.md"):
            source_file = f
            break

        if not source_file or not source_file.exists():
            print(f"  ⚠️  找不到源文件: {candidate.id}")
            return

        # 确定目标目录
        target_dir = self.approved_dir if status == "approved" else self.rejected_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # 读取并更新内容
        content = source_file.read_text(encoding='utf-8')
        content = content.replace(
            'review_status: "pending"',
            f'review_status: "{status}"\nreviewed_by: "user"\nreviewed_at: "{datetime.now(timezone.utc).isoformat()}"'
        )

        if feedback:
            content = content.replace(
                '---\n\n',
                f'---\nuser_feedback: "{feedback}"\n\n'
            )

        # 保存到目标目录
        target_file = target_dir / source_file.name
        target_file.write_text(content, encoding='utf-8')

        # 删除源文件
        source_file.unlink()

        print(f"  📦 已归档到 candidate/{status}/")


class SemanticMemoryManager:
    """语义记忆管理器"""

    def __init__(self):
        self.memory_base = REPO_PATH / "memory"

    def promote_from_candidate(self, candidate: CandidateMemory) -> SemanticMemory:
        """将候选提升为语义记忆"""

        # 确定 tier
        tier = self._determine_tier(candidate)

        # 创建 memory
        memory = SemanticMemory(
            id=str(uuid.uuid4()),
            context_type=candidate.candidate_for,
            content=candidate.content,
            memory_tier=tier,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            confidence=candidate.confidence_score,
            verified_by="user",
            verified_at=datetime.now(timezone.utc).isoformat(),
            replaces=[]
        )

        # 保存
        self._save_memory(memory)

        return memory

    def _determine_tier(self, candidate: CandidateMemory) -> str:
        """确定 memory tier"""
        # Core: 高重要性 + 长期类型
        if candidate.candidate_for in ['preference', 'principle']:
            if candidate.importance_score >= 8:
                return "core"

        if candidate.candidate_for == 'decision' and candidate.importance_score >= 9:
            return "core"

        return "active"

    def _save_memory(self, memory: SemanticMemory):
        """保存语义记忆"""
        type_dir = self.memory_base / memory.memory_tier / f"{memory.context_type}s"
        type_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{memory.context_type}-{timestamp}-{memory.id[:8]}.md"
        filepath = type_dir / filename

        # 计算 TTL
        config = ConfigManager()
        ttl_config = config.get(f"memory_os.ttl.{memory.context_type}")
        ttl_days = ttl_config if ttl_config else 365

        yaml_content = f"""---
context_id: "{memory.id}"
context_type: "{memory.context_type}"
version: "1.0.0"
created_at: "{memory.created_at}"
updated_at: "{memory.updated_at}"
memory_tier: "{memory.memory_tier}"
ttl_days: {ttl_days}
access_count: {memory.access_count}
confidence: {memory.confidence:.2f}
verified_by: "{memory.verified_by}"
verified_at: "{memory.verified_at}"
tags: ["from-candidate"]
---

{memory.content}
"""

        filepath.write_text(yaml_content, encoding='utf-8')
        print(f"  ✅ 已创建 memory/{memory.memory_tier}/{memory.context_type}s/{filename}")

    def load_all_memories(self) -> List[SemanticMemory]:
        """加载所有语义记忆"""
        memories = []

        for tier in ['core', 'active']:
            tier_dir = self.memory_base / tier
            if not tier_dir.exists():
                continue

            for type_dir in tier_dir.iterdir():
                if type_dir.is_dir():
                    for mem_file in type_dir.glob("*.md"):
                        memory = self._parse_memory_file(mem_file)
                        if memory:
                            memories.append(memory)

        return memories

    def _parse_memory_file(self, file_path: Path) -> Optional[SemanticMemory]:
        """解析记忆文件"""
        try:
            content = file_path.read_text(encoding='utf-8')

            if not content.startswith('---'):
                return None

            parts = content.split('---', 2)
            if len(parts) < 3:
                return None

            import yaml
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()

            return SemanticMemory(
                id=frontmatter.get('context_id', ''),
                context_type=frontmatter.get('context_type', 'memory'),
                content=body,
                memory_tier=frontmatter.get('memory_tier', 'active'),
                created_at=frontmatter.get('created_at', ''),
                updated_at=frontmatter.get('updated_at', ''),
                ttl_days=frontmatter.get('ttl_days'),
                access_count=frontmatter.get('access_count', 0),
                last_accessed=frontmatter.get('last_accessed'),
                confidence=frontmatter.get('confidence', 0),
                verified_by=frontmatter.get('verified_by', 'user'),
                verified_at=frontmatter.get('verified_at'),
                replaces=frontmatter.get('replaces', []),
                version=frontmatter.get('version', 1)
            )
        except Exception as e:
            return None


class ReviewManager:
    """审核管理器"""

    def __init__(self):
        self.candidate_manager = CandidateManager()
        self.memory_manager = SemanticMemoryManager()
        self.config = ConfigManager()

    def should_auto_approve(self, candidate: CandidateMemory) -> bool:
        """判断是否应自动通过"""
        threshold = self.config.get("memory_os.review.auto_promote_threshold", {})
        min_confidence = threshold.get("confidence", 0.9)
        min_importance = threshold.get("importance", 8)

        # 类型特定的规则
        if candidate.candidate_for == "preference":
            if candidate.confidence_score >= 0.85:
                return True

        return (
            candidate.confidence_score >= min_confidence and
            candidate.importance_score >= min_importance
        )

    def review_candidates(self, auto_mode: bool = False) -> Tuple[int, int]:
        """审核候选列表"""
        candidates = self.candidate_manager.load_pending_candidates()

        if not candidates:
            print("✅ 没有待审核的候选记忆")
            return 0, 0

        print(f"\n📋 发现 {len(candidates)} 个待审核候选\n")

        approved_count = 0
        rejected_count = 0

        for i, candidate in enumerate(candidates, 1):
            print(f"\n[候选 {i}/{len(candidates)}]")

            if auto_mode:
                if self.should_auto_approve(candidate):
                    print(f"  ✅ 自动通过: {candidate.id[:8]}")
                    self._approve_candidate(candidate)
                    approved_count += 1
                else:
                    print(f"  ⏸️  跳过（需人工审核）: {candidate.id[:8]}")
            else:
                action = self._interactive_review(candidate)

                if action == "approve":
                    self._approve_candidate(candidate)
                    approved_count += 1
                elif action == "reject":
                    self._reject_candidate(candidate)
                    rejected_count += 1
                elif action == "modify":
                    modified = self._modify_candidate(candidate)
                    if modified:
                        self._approve_candidate(modified)
                        approved_count += 1

        print(f"\n{'='*60}")
        print(f"✅ 审核完成: {approved_count} 通过, {rejected_count} 拒绝")

        return approved_count, rejected_count

    def _interactive_review(self, candidate: CandidateMemory) -> str:
        """交互式审核单个候选"""
        print(f"\n{'='*60}")
        print(f"📝 候选记忆 ({candidate.id[:8]}...)")
        print(f"{'='*60}")
        print(f"类型: {candidate.candidate_for}")
        print(f"重要性: {candidate.importance_score}/10")
        print(f"置信度: {candidate.confidence_score:.2f}")
        print(f"提取方式: {candidate.extraction_method}")
        print(f"\n内容:\n{candidate.content[:400]}...")
        print(f"\n{'='*60}")

        while True:
            try:
                choice = input("[a]pprove / [r]eject / [m]odify / [s]kip? ").lower().strip()
                if choice in ['a', 'approve', '']:
                    return "approve"
                elif choice in ['r', 'reject']:
                    return "reject"
                elif choice in ['m', 'modify']:
                    return "modify"
                elif choice in ['s', 'skip']:
                    return "skip"
                else:
                    print("  无效输入，请重试")
            except (EOFError, KeyboardInterrupt):
                print("\n  跳过")
                return "skip"

    def _approve_candidate(self, candidate: CandidateMemory):
        """批准候选"""
        # 提升为 memory
        self.memory_manager.promote_from_candidate(candidate)

        # 归档候选
        self.candidate_manager.archive_candidate(candidate, "approved")

    def _reject_candidate(self, candidate: CandidateMemory):
        """拒绝候选"""
        self.candidate_manager.archive_candidate(candidate, "rejected")

    def _modify_candidate(self, candidate: CandidateMemory) -> Optional[CandidateMemory]:
        """修改候选"""
        print(f"\n✏️  修改内容（直接输入新内容，空行结束）:")
        print(f"  原内容: {candidate.content[:100]}...")
        print(f"  提示: 输入新内容后按回车两次结束\n")

        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break

        if not lines:
            print("  未修改，跳过")
            return None

        new_content = "\n".join(lines)
        candidate.content = new_content

        # 更新重要性（可选）
        try:
            new_importance = input(f"\n重要性评分 ({candidate.importance_score}): ").strip()
            if new_importance:
                candidate.importance_score = float(new_importance)
        except:
            pass

        return candidate


# ============================================
# 对外接口
# ============================================

def create_candidate_from_analysis(
    content: str,
    candidate_for: str = "memory",
    importance_score: float = 5.0,
    confidence_score: float = 0.6,
    source_session: str = ""
) -> CandidateMemory:
    """从分析结果创建候选"""
    manager = CandidateManager()
    return manager.create_candidate(
        content=content,
        candidate_for=candidate_for,
        importance_score=importance_score,
        confidence_score=confidence_score,
        source_session=source_session
    )


def review_all_candidates(auto_mode: bool = False) -> Tuple[int, int]:
    """审核所有候选"""
    manager = ReviewManager()
    return manager.review_candidates(auto_mode=auto_mode)


def list_pending_candidates() -> List[CandidateMemory]:
    """列出所有待审核候选"""
    manager = CandidateManager()
    return manager.load_pending_candidates()


def get_memory_stats() -> Dict:
    """获取记忆统计"""
    manager = SemanticMemoryManager()
    memories = manager.load_all_memories()

    stats = {
        "total": len(memories),
        "by_tier": {},
        "by_type": {},
        "core_count": 0,
        "active_count": 0
    }

    for mem in memories:
        # By tier
        tier = mem.memory_tier
        stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1

        # By type
        mem_type = mem.context_type
        stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1

    stats["core_count"] = stats["by_tier"].get("core", 0)
    stats["active_count"] = stats["by_tier"].get("active", 0)

    return stats


if __name__ == "__main__":
    # 测试
    print("Memory OS v2.0 Core Module")
    print("Run 'review_all_candidates()' to test")
