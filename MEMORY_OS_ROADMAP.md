# Memory OS 升级执行计划

> 最小侵入式迁移路径：从 v1 到 v2

---

## 📋 阶段概览

```
Phase 1: 基础架构 (1-2天)
    ├── 创建新目录结构
    ├── 扩展 Schema (candidate_memory)
    └── 配置升级 (config.yml v2)

Phase 2: 核心流程 (2-3天)
    ├── 改造 suggest → create_candidate
    ├── 实现 review 命令
    └── 实现 promote/reject 命令

Phase 3: Active Context (1-2天)
    ├── 实现 active-context.yaml
    ├── 创建 context-builder
    └── focus 命令

Phase 4: Memory 控制 (2-3天)
    ├── Deduplication
    ├── TTL & Archival
    └── Size limits

Phase 5: 测试 & 迁移 (1-2天)
    ├── 迁移脚本
    ├── 测试验证
    └── 文档更新
```

---

## 🚀 Phase 1: 基础架构

### 任务 1.1: 创建目录结构

```bash
#!/bin/bash
# scripts/init-v2-structure.sh

cd "$CONTEXT_SYNC_REPO"

# Logs 层
mkdir -p logs/{sessions,summaries,milestones,auto}

# Candidate 层
mkdir -p candidate/{pending,approved,rejected}

# Memory 层（收紧定义）
mkdir -p memory/core/{preferences,decisions,principles}
mkdir -p memory/active/{facts,goals}
mkdir -p memory/archive/{preferences,decisions,principles,facts,goals}

# State
mkdir -p .context/state

# 创建 .gitkeep
touch logs/sessions/.gitkeep
touch candidate/pending/.gitkeep

echo "✅ v2 目录结构创建完成"
```

### 任务 1.2: Schema 扩展

```python
# schema/v2.py

CANDIDATE_MEMORY_SCHEMA = {
    "context_type": "candidate_memory",
    "required_fields": [
        "context_id",
        "candidate_for",      # "memory" | "preference" | "decision" | "principle"
        "importance_score",   # 0-10
        "confidence_score",   # 0-1
        "extraction_method",  # "ai" | "rule"
        "source_session",
        "proposed_at",
        "content"
    ],
    "optional_fields": [
        "review_status",      # "pending" | "approved" | "rejected"
        "reviewed_by",
        "reviewed_at",
        "user_feedback"       # 用户审核时的注释
    ]
}

SEMANTIC_MEMORY_SCHEMA = {
    "context_type": ["memory", "preference", "decision", "principle", "fact", "goal"],
    "required_fields": [
        "context_id",
        "content",
        "memory_tier",        # "core" | "active" | "archived"
        "verified_at"
    ],
    "optional_fields": [
        "ttl_days",
        "access_count",
        "last_accessed",
        "confidence",
        "verified_by",        # "user" | "auto"
        "replaces",           # 替换的旧记忆ID列表
        "version"             # 版本号
    ]
}
```

### 任务 1.3: 配置升级

```yaml
# .context/config.yml v2.0

version: "2.0.0"

# 保留 v1 配置
user:
  id: "Jxy-yxJ"
  
sync:
  mode: "hybrid"
  auto_push: false
  auto_pull: true

# 新增：Memory OS 配置
memory_os:
  enabled: true
  
  # Candidate Memory 配置
  candidate:
    auto_extract: true
    min_confidence: 0.6      # 最低置信度
    min_importance: 5        # 最低重要性
    
  # 审核配置
  review:
    mode: "manual"           # "manual" | "auto" | "hybrid"
    auto_promote_threshold:
      confidence: 0.9
      importance: 8
    require_reason: true     # 要求提供审核理由
    
  # Memory 控制
  control:
    max_total: 1000
    max_per_type:
      preference: 100
      decision: 200
      principle: 50
      fact: 500
      goal: 50
    deduplication: true
    compression: true
    
  # Active Context
  active_context:
    enabled: true
    auto_build: true
    token_budget: 8000
    core_memory_required: true
```

---

## 🔄 Phase 2: 核心流程

### 任务 2.1: 改造 suggest 命令

```python
# auto-sync.py

def suggest(content=None):
    """
    v2: suggest 不再直接创建 memory，而是创建 candidate
    """
    # 1. 分析工作
    analysis = analyze_current_work()
    
    # 2. 提取候选
    candidates = extract_candidates(analysis, content)
    
    # 3. 评分
    for candidate in candidates:
        candidate.importance_score = score_importance(candidate)
        candidate.confidence_score = score_confidence(candidate)
    
    # 4. 过滤低质量
    config = get_config()
    min_conf = config['memory_os']['candidate']['min_confidence']
    min_imp = config['memory_os']['candidate']['min_importance']
    
    candidates = [
        c for c in candidates 
        if c.confidence_score >= min_conf and c.importance_score >= min_imp
    ]
    
    # 5. 创建 candidate_memory 文件
    for candidate in candidates:
        create_candidate_file(candidate)
    
    # 6. 更新审核队列
    update_review_queue(candidates)
    
    # 7. 显示给用户
    display_candidates_for_review(candidates)
    
    # 8. 提示审核
    if candidates:
        print(f"\n💡 发现 {len(candidates)} 个候选记忆")
        print("运行 `auto-sync.py review` 进行审核\n")
    
    return candidates


def create_candidate_file(candidate):
    """创建 candidate_memory 文件"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"candidate-{timestamp}-{candidate.id[:8]}.md"
    filepath = REPO_PATH / "candidate" / "pending" / filename
    
    content = f"""---
context_id: "{candidate.id}"
context_type: "candidate_memory"
candidate_for: "{candidate.target_type}"
importance_score: {candidate.importance_score}
confidence_score: {candidate.confidence_score}
extraction_method: "{candidate.extraction_method}"
source_session: "{candidate.source_session}"
proposed_at: "{datetime.now().isoformat()}"
review_status: "pending"
---

{candidate.content}
"""
    
    filepath.write_text(content, encoding='utf-8')
    print(f"  📝 候选: {filename} (importance: {candidate.importance_score}, confidence: {candidate.confidence_score:.2f})")
```

### 任务 2.2: 实现 review 命令

```python
def review(auto_mode=False):
    """
    审核候选记忆
    """
    # 1. 加载待审核列表
    candidates = load_pending_candidates()
    
    if not candidates:
        print("✅ 没有待审核的候选记忆")
        return
    
    approved = []
    rejected = []
    
    for candidate in candidates:
        if auto_mode:
            # 自动模式：高置信度自动通过
            if should_auto_approve(candidate):
                approved.append(candidate)
                print(f"✅ 自动通过: {candidate.id}")
            else:
                print(f"⏸️  跳过（需人工审核）: {candidate.id}")
        else:
            # 交互式审核
            action = interactive_review(candidate)
            
            if action == "approve":
                approved.append(candidate)
            elif action == "reject":
                rejected.append(candidate)
            elif action == "modify":
                modified = edit_candidate(candidate)
                approved.append(modified)
            # "skip" - 保持 pending
    
    # 处理审核结果
    for candidate in approved:
        promote_to_memory(candidate)
        archive_candidate(candidate, "approved")
    
    for candidate in rejected:
        archive_candidate(candidate, "rejected")
    
    print(f"\n✅ 审核完成: {len(approved)} 通过, {len(rejected)} 拒绝")
    
    # 自动推送
    if approved or rejected:
        sync_push()


def interactive_review(candidate):
    """交互式审核单个候选"""
    print(f"\n{'='*60}")
    print(f"📝 候选记忆 ({candidate.id})")
    print(f"{'='*60}")
    print(f"类型: {candidate.candidate_for}")
    print(f"重要性: {candidate.importance_score}/10")
    print(f"置信度: {candidate.confidence_score:.2f}")
    print(f"来源: {candidate.source_session}")
    print(f"\n内容:\n{candidate.content[:500]}...")
    print(f"\n{'='*60}")
    
    while True:
        choice = input("[a]pprove / [r]eject / [m]odify / [s]kip? ").lower()
        if choice in ['a', 'approve']:
            return "approve"
        elif choice in ['r', 'reject']:
            return "reject"
        elif choice in ['m', 'modify']:
            return "modify"
        elif choice in ['s', 'skip']:
            return "skip"
```

### 任务 2.3: 实现 promote/reject

```python
def promote_to_memory(candidate):
    """将 candidate 提升为 semantic memory"""
    
    # 确定目标目录
    target_type = candidate.candidate_for  # preference/decision/principle/fact/goal
    tier = "active"  # 默认 active
    
    # core 类型的判断逻辑
    if target_type in ['preference', 'decision', 'principle']:
        if candidate.importance_score >= 9:
            tier = "core"
    
    # 生成目标路径
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{target_type}-{timestamp}-{candidate.id[:8]}.md"
    target_dir = REPO_PATH / "memory" / tier / f"{target_type}s"
    target_path = target_dir / filename
    
    # 构建 memory 内容
    memory_content = f"""---
context_id: "{uuid4()}"
context_type: "{target_type}"
version: "1.0.0"
created_at: "{datetime.now().isoformat()}"
updated_at: "{datetime.now().isoformat()}"
memory_tier: "{tier}"
ttl_days: 365
access_count: 0
confidence: {candidate.confidence_score}
verified_by: "user"
verified_at: "{datetime.now().isoformat()}"
source_candidate: "{candidate.id}"
tags: ["promoted-from-candidate"]
---

{candidate.content}
"""
    
    target_path.write_text(memory_content, encoding='utf-8')
    print(f"  ✅ 已创建 memory: memory/{tier}/{target_type}s/{filename}")
    
    # 更新索引
    update_memory_index(target_type, target_path)


def archive_candidate(candidate, status):
    """归档已处理的 candidate"""
    source_path = candidate.filepath
    target_dir = REPO_PATH / "candidate" / ("approved" if status == "approved" else "rejected")
    target_path = target_dir / source_path.name
    
    # 更新内容，添加审核信息
    content = source_path.read_text(encoding='utf-8')
    content = content.replace(
        "review_status: \"pending\"",
        f"review_status: \"{status}\"\nreviewed_by: \"user\"\nreviewed_at: \"{datetime.now().isoformat()}\""
    )
    
    target_path.write_text(content, encoding='utf-8')
    source_path.unlink()  # 删除原文件
    
    print(f"  📦 已归档到 candidate/{status}/")
```

---

## 🎯 Phase 3: Active Context

### 任务 3.1: 实现 active-context.yaml

```python
def focus_set(project=None, task=None, goal=None):
    """设置当前 focus"""
    
    active_context = {
        "version": "2.0.0",
        "updated_at": datetime.now().isoformat(),
        "focus": {
            "type": "project" if project else "task",
            "project_id": project,
            "task_id": task,
            "goal": goal
        },
        "memory": {
            "core": ["memory/core/**/*"],
            "active": {
                "pattern": "memory/active/**/*",
                "filter": {
                    "tags": [],
                    "last_accessed_within": "30d"
                }
            }
        },
        "token_budget": {
            "max_total": 8000,
            "memory_allocation": 0.4
        }
    }
    
    # 如果设置了 project，加载相关 tags
    if project:
        project_context = load_project_context(project)
        active_context["memory"]["active"]["filter"]["tags"] = project_context.get("tags", [])
    
    # 保存
    state_path = REPO_PATH / ".context" / "state" / "active-context.yaml"
    with open(state_path, 'w', encoding='utf-8') as f:
        yaml.dump(active_context, f, allow_unicode=True, sort_keys=False)
    
    print(f"✅ Focus 已设置: {goal or project or task}")


def focus_get():
    """获取当前 focus"""
    state_path = REPO_PATH / ".context" / "state" / "active-context.yaml"
    
    if not state_path.exists():
        print("❌ 未设置 focus")
        return None
    
    with open(state_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
```

### 任务 3.2: Context Builder

```python
class ContextBuilder:
    """构建模型输入的上下文"""
    
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.active_context = self._load_active_context()
        self.token_budget = self.active_context.get("token_budget", {}).get("max_total", 8000)
        self.used_tokens = 0
    
    def build(self):
        """构建完整上下文"""
        parts = []
        
        # 1. System prompt
        parts.append(self._get_system_prompt())
        
        # 2. Core Memory (必须加载)
        parts.append(self._load_core_memories())
        
        # 3. Active Memory (根据 focus 选择)
        parts.append(self._load_active_memories())
        
        # 4. Project Context
        if self.active_context.get("focus", {}).get("project_id"):
            parts.append(self._load_project_context())
        
        # 5. Recent Sessions
        parts.append(self._load_recent_sessions())
        
        return self._assemble(parts)
    
    def _load_core_memories(self):
        """加载核心记忆"""
        core_memories = []
        core_dir = self.repo_path / "memory" / "core"
        
        for type_dir in ["preferences", "decisions", "principles"]:
            type_path = core_dir / type_dir
            if type_path.exists():
                for mem_file in sorted(type_path.glob("*.md")):
                    core_memories.append(self._read_memory(mem_file))
        
        return {
            "priority": 90,
            "content": "\n\n".join(core_memories),
            "type": "core_memory"
        }
    
    def _load_active_memories(self):
        """加载活跃记忆（带预算控制）"""
        budget = int(self.token_budget * 0.4)  # 40% 给 memory
        memories = []
        
        active_dir = self.repo_path / "memory" / "active"
        
        # 按最后访问时间排序
        all_memories = []
        for mem_file in active_dir.rglob("*.md"):
            mem = self._parse_memory(mem_file)
            all_memories.append((mem.get("last_accessed", ""), mem_file, mem))
        
        all_memories.sort(reverse=True)  # 最新的在前
        
        # 按预算选择
        current_tokens = 0
        for _, mem_file, mem in all_memories:
            content = mem.get("content", "")
            tokens = self._estimate_tokens(content)
            
            if current_tokens + tokens > budget:
                break
            
            memories.append(content)
            current_tokens += tokens
            
            # 更新访问计数
            self._update_access_count(mem_file)
        
        return {
            "priority": 80,
            "content": "\n\n".join(memories),
            "type": "active_memory"
        }
    
    def _estimate_tokens(self, text):
        """估算 token 数（粗略）"""
        return len(text) // 4  # 中文约 1:4
```

---

## 🧠 Phase 4: Memory 控制

### 任务 4.1: Deduplication

```python
def deduplicate_candidates(candidates=None):
    """
    去重：检查 candidates 之间，以及 candidates 与现有 memory
    """
    if candidates is None:
        candidates = load_pending_candidates()
    
    # 1. candidates 之间去重
    to_remove = set()
    for i, c1 in enumerate(candidates):
        for j, c2 in enumerate(candidates[i+1:], i+1):
            sim = semantic_similarity(c1.content, c2.content)
            if sim > 0.85:
                # 保留置信度高的
                if c1.confidence_score > c2.confidence_score:
                    to_remove.add(j)
                else:
                    to_remove.add(i)
    
    candidates = [c for i, c in enumerate(candidates) if i not in to_remove]
    
    # 2. 与现有 memory 去重
    for candidate in candidates[:]:  # copy for safe removal
        similar = find_similar_memories(candidate.content, threshold=0.8)
        if similar:
            print(f"⚠️  Candidate {candidate.id} 与现有 memory {similar[0].id} 重复")
            archive_candidate(candidate, "duplicate")
            candidates.remove(candidate)
    
    return candidates


def semantic_similarity(text1, text2):
    """计算语义相似度（简化版：关键词重叠）"""
    # 实际实现可使用 embeddings
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    overlap = words1 & words2
    return len(overlap) / max(len(words1), len(words2))
```

### 任务 4.2: TTL & Archival

```python
def memory_maintenance():
    """定期维护 memory"""
    config = get_config()
    limits = config['memory_os']['control']
    
    archived_count = 0
    
    for memory_file in (REPO_PATH / "memory").rglob("*.md"):
        mem = parse_memory_file(memory_file)
        age_days = (datetime.now() - mem.created_at).days
        
        # 检查 TTL
        if mem.ttl_days and age_days > mem.ttl_days:
            if mem.access_count < 3:
                # 很少访问，归档
                archive_memory(memory_file)
                archived_count += 1
            else:
                # 延长 TTL
                mem.ttl_days += 180
                update_memory_file(memory_file, mem)
        
        # 检查过期决策
        if mem.context_type == "decision" and age_days > 180:
            mem.status = "review_needed"
            update_memory_file(memory_file, mem)
    
    # 检查总量限制
    enforce_size_limits(limits)
    
    print(f"✅ 维护完成: {archived_count} 个 memory 归档")


def enforce_size_limits(limits):
    """强制执行 size limits"""
    for mem_type, max_count in limits.get("max_per_type", {}).items():
        type_files = list((REPO_PATH / "memory").rglob(f"{mem_type}*.md"))
        
        if len(type_files) > max_count:
            # 按访问时间排序，归档最老的
            type_files.sort(key=lambda f: f.stat().st_atime)
            to_archive = type_files[:-max_count]  # 保留最新的
            
            for f in to_archive:
                archive_memory(f)
                print(f"  📦 归档 (超限制): {f.name}")
```

---

## 🧪 Phase 5: 迁移 & 测试

### 任务 5.1: 迁移脚本

```python
#!/usr/bin/env python3
"""
Migrate v1 -> v2
将现有 memory 分类到 semantic types
"""

import shutil
from pathlib import Path

def migrate_v1_to_v2():
    """迁移现有数据"""
    repo = Path("D:/Coding/context-sync-data")
    
    print("🚀 开始 v1 -> v2 迁移")
    
    # 1. 创建目录结构
    init_v2_structure()
    
    # 2. 迁移现有 memory
    memory_dir = repo / "memory" / "user"
    if memory_dir.exists():
        for mem_file in memory_dir.rglob("*.md"):
            classify_and_move_memory(mem_file)
    
    # 3. 迁移 sessions -> logs/sessions
    sessions_dir = repo / "sessions"
    if sessions_dir.exists():
        for session_file in sessions_dir.rglob("*.md"):
            target = repo / "logs" / "sessions" / session_file.relative_to(sessions_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(session_file, target)
    
    print("✅ 迁移完成！")
    print("\n⚠️  重要提示:")
    print("1. 请检查 memory/core/ 下的内容")
    print("2. 运行 `auto-sync.py review` 审核候选")
    print("3. 更新 config.yml 启用 v2 功能")


def classify_and_move_memory(mem_file):
    """分类并移动 memory"""
    content = mem_file.read_text(encoding='utf-8')
    
    # 简单启发式分类
    if "偏好" in content or "喜欢" in content or "prefer" in content.lower():
        target_type = "preference"
        tier = "active"
    elif "决策" in content or "决定" in content or "decide" in content.lower():
        target_type = "decision"
        tier = "active"
    elif "原则" in content or "总是" in content or "principle" in content.lower():
        target_type = "principle"
        tier = "core"
    else:
        target_type = "fact"
        tier = "active"
    
    # 移动文件
    target_dir = Path("D:/Coding/context-sync-data") / "memory" / tier / f"{target_type}s"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = target_dir / mem_file.name
    shutil.move(mem_file, target_file)
    
    print(f"  📁 {mem_file.name} -> memory/{tier}/{target_type}s/")


if __name__ == "__main__":
    migrate_v1_to_v2()
```

### 任务 5.2: 测试清单

```markdown
## 测试清单

### 功能测试

- [ ] suggest 创建 candidate（不是 memory）
- [ ] review 交互式审核
- [ ] review --auto 自动审核
- [ ] promote 提升为 memory
- [ ] reject 拒绝 candidate
- [ ] focus set/get/clear
- [ ] context-builder 正确组装

### 边界测试

- [ ] 空 candidate 队列
- [ ] 重复 candidate 检测
- [ ] 超过 size limits
- [ ] TTL 过期处理
- [ ] 损坏的 memory 文件

### 回归测试

- [ ] v1 命令仍然工作
- [ ] summary 生成正确
- [ ] push/pull 正常
- [ ] Obsidian 同步正常
```

---

## 📊 预期成果

### 迁移前 (v1)
```
memory/
├── user/
│   ├── 100001-xxxx-完成了登录功能.md
│   ├── 100002-xxxx-喜欢使用Python.md
│   ├── 100003-xxxx-决定使用JWT.md
│   └── ... (100+ 个文件，混乱)
```

### 迁移后 (v2)
```
memory/
├── core/
│   ├── preferences/
│   │   └── preference-xxx-喜欢使用Python.md
│   ├── decisions/
│   │   └── decision-xxx-使用JWT认证.md
│   └── principles/
│       └── principle-xxx-代码简洁优先.md
├── active/
│   ├── facts/
│   │   └── fact-xxx-API文档地址.md
│   └── goals/
│       └── goal-xxx-完成项目A.md
└── archive/
    └── ... (过期的)

candidate/
└── pending/
    └── candidate-xxx-待审核内容.md

logs/
├── sessions/
├── summaries/
└── milestones/
```

---

## 🎯 成功标准

1. **suggest 不直接写 memory** ✅
2. **candidate 有审核流程** ✅
3. **memory 有分层结构** ✅
4. **有 Active Context 机制** ✅
5. **CLI 体验保持一致** ✅
6. **现有数据不丢失** ✅

---

*Plan Version: 1.0*
*Estimated Time: 7-10 days*
