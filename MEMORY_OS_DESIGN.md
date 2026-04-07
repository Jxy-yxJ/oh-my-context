# Memory OS 架构升级设计

> 从 "增强笔记" 到 "有纪律的 Memory OS"
> 版本: v2.0 - Minimal Intrusive Upgrade

---

## 📋 设计目标

**不改变现有 CLI 体验**，实现：
- ✅ 三层结构分离 (Logs → Candidate → Memory)
- ✅ Memory 定义收紧（只有稳定认知）
- ✅ AI 不能直接写入 Memory
- ✅ 可控的 Memory 增长
- ✅ 可审计、可扩展

---

## 🏗️ 核心架构变化

### 1. 三层数据流

```
┌─────────────────────────────────────────────────────────────┐
│                     LOGS / SESSION                          │
│  (高频、append-only、短期)                                    │
│  • session/    - 对话记录                                    │
│  • summary/    - 会话总结                                    │
│  • milestone/  - 里程碑                                      │
│  • logs/       - 执行日志                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │  AI提取 / 规则匹配
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  CANDIDATE MEMORY                           │
│  (待审核、带评分、带来源)                                      │
│  • candidate/  - 候选记忆                                    │
│    - importance_score (0-10)                                │
│    - confidence_score (0-1)                                 │
│    - source_session (溯源)                                   │
└─────────────────────────┬───────────────────────────────────┘
                          │ 人工审核 / 高置信度自动通过
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 SEMANTIC MEMORY                             │
│  (长期、稳定、影响决策)                                        │
│  • memory/     - 语义记忆                                    │
│    - preference/  - 稳定偏好                                 │
│    - decision/    - 已确认决策                               │
│    - principle/   - 可复用原则                               │
│    - fact/        - 稳定事实                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2. 类型系统重构

```yaml
# 现有类型保持不变，新增语义分层
context_type:
  # === RECORD 类（事件流）===
  - session      # 对话记录
  - summary      # 会话总结  
  - milestone    # 里程碑
  - log          # 执行日志
  
  # === CANDIDATE 类（新增）===
  - candidate_memory    # 候选记忆（AI提取）
  
  # === KNOWLEDGE 类（长期认知）===
  - memory       # 语义记忆（总类）
  - preference   # 稳定偏好
  - decision     # 已确认决策
  - principle    # 可复用原则
  - fact         # 稳定事实
  - goal         # 长期目标
  
  # === PROJECT 类（保持不变）===
  - project      # 项目
  - task         # 任务
```

### 3. Context Schema 扩展

```yaml
# === CANDIDATE MEMORY 特有字段 ===
context_type: "candidate_memory"
candidate_for: "memory"           # 目标类型
importance_score: 7.5             # 重要性评分 (0-10)
confidence_score: 0.75            # 置信度 (0-1)
extraction_method: "ai" | "rule"  # 提取方式
source_session: "session-uuid"    # 来源会话
proposed_at: "2026-04-07T10:30:00Z"
review_status: "pending" | "approved" | "rejected"
reviewed_by: "user" | "auto"      # 审核者
reviewed_at: "2026-04-07T11:00:00Z"

# === SEMANTIC MEMORY 特有字段 ===
context_type: "memory" | "preference" | "decision" | "principle" | "fact"
memory_tier: "core" | "active" | "archived"  # 层级
ttl_days: 365                     # 有效期（天）
access_count: 42                  # 访问次数
last_accessed: "2026-04-07T10:00:00Z"
confidence: 0.95                  # 确认后的置信度
verified_by: "user" | "auto"      # 验证方式
verified_at: "2026-04-07T10:00:00Z"
replaces: ["old-memory-uuid"]     # 替换的旧记忆
```

---

## 🔄 核心流程设计

### 1. Candidate Memory 生成流程

```python
def suggest_flow():
    """
    新的 suggest 流程（不直接创建 memory）
    """
    # 1. 分析当前工作
    analysis = analyze_current_work()
    
    # 2. 提取候选记忆
    candidates = extract_candidates(analysis)
    
    # 3. 评分
    for candidate in candidates:
        candidate.importance_score = calculate_importance(candidate)
        candidate.confidence_score = calculate_confidence(candidate)
    
    # 4. 过滤低质量
    candidates = filter(c for c in candidates if c.confidence_score > 0.6)
    
    # 5. 创建 candidate_memory（不是 memory）
    for candidate in candidates:
        create_candidate_memory(candidate)
    
    # 6. 提示用户审核
    prompt_user_review(candidates)
```

### 2. Review / Promote 机制

```python
def review_candidate(candidate_id):
    """
    审核候选记忆
    """
    candidate = load_candidate(candidate_id)
    
    # 显示给用户
    display_for_review(candidate)
    
    # 用户决策
    action = user_select(["approve", "reject", "modify", "skip"])
    
    if action == "approve":
        # 提升到 semantic memory
        promote_to_memory(candidate)
        archive_candidate(candidate, "approved")
        
    elif action == "reject":
        # 拒绝，保留在 logs
        archive_candidate(candidate, "rejected")
        
    elif action == "modify":
        # 修改后批准
        modified = user_edit(candidate)
        promote_to_memory(modified)
        archive_candidate(candidate, "modified")
```

### 3. Auto-Promote 规则（高置信度）

```yaml
# 配置在 config.yml
auto_promote:
  enabled: true
  rules:
    - condition: "confidence_score > 0.9 AND importance_score > 8"
      action: "auto_approve"
    - condition: "type == 'preference' AND confidence_score > 0.85"
      action: "auto_approve"
    - condition: "type == 'decision' AND user_confirmed == true"
      action: "auto_approve"
```

---

## 📁 目录结构升级

```
context-sync-data/
├── .context/
│   ├── config.yml              # 配置（扩展）
│   ├── state/
│   │   ├── active-context.yaml # 新增：当前激活上下文
│   │   ├── session-state.json  # 会话状态
│   │   └── review-queue.json   # 新增：待审核队列
│   └── memory-index.json       # 新增：Memory 索引
│
├── logs/                       # 新增：统一日志目录
│   ├── sessions/               # 原有：对话记录
│   ├── summaries/              # 原有：会话总结
│   ├── milestones/             # 新增：里程碑
│   └── auto/                   # 新增：自动日志
│
├── candidate/                  # 新增：候选记忆
│   ├── pending/                # 待审核
│   ├── approved/               # 已批准（归档）
│   └── rejected/               # 已拒绝（归档）
│
├── memory/                     # 收紧定义
│   ├── core/                   # 核心记忆（必须加载）
│   │   ├── preferences/        # 稳定偏好
│   │   ├── decisions/          # 关键决策
│   │   └── principles/         # 核心原则
│   ├── active/                 # 活跃记忆（按需加载）
│   │   ├── facts/              # 稳定事实
│   │   └── goals/              # 当前目标
│   └── archive/                # 归档记忆（历史）
│       └── decisions/          # 过期决策
│
├── projects/                   # 保持不变
├── tasks/                      # 保持不变
└── shared/                     # 保持不变
```

---

## 🎯 Active Context 机制

### 1. 新增 state/active-context.yaml

```yaml
# 当前激活上下文配置
version: "2.0.0"
updated_at: "2026-04-07T10:30:00Z"

# 当前 Focus
focus:
  type: "project" | "task" | "learning"
  project_id: "project-uuid"      # 当前项目
  task_id: "task-uuid"            # 当前任务
  goal: "实现用户登录功能"

# Memory 加载策略
memory:
  # 必须加载的核心记忆
  core:
    - memory/core/preferences/*.md
    - memory/core/decisions/project-auth.md
  
  # 根据 focus 动态加载
  active:
    pattern: "memory/active/**/*"
    filter:
      tags: ["auth", "security"]
      last_accessed_within: "30d"
  
  # 排除项
  exclude:
    - memory/archive/**
    - "*deprecated*"

# Token 预算控制
token_budget:
  max_total: 8000
  memory_allocation: 0.4          # 40% 给 memory
  context_allocation: 0.6         # 60% 给当前上下文

# 上下文组装顺序
context_build:
  order:
    - type: "system"              # 系统提示
      priority: 100
    - type: "core_memory"         # 核心记忆
      priority: 90
    - type: "active_memory"       # 活跃记忆
      priority: 80
      limit: 2000                 # Token 限制
    - type: "project_context"     # 项目上下文
      priority: 70
    - type: "session_history"     # 会话历史
      priority: 60
      limit: 1000
```

### 2. Context 构建器

```python
def build_context(active_context_config):
    """
    根据 active-context.yaml 构建模型输入
    """
    context_parts = []
    budget = active_context_config.token_budget
    
    # 1. 加载核心记忆（必须）
    core_memories = load_core_memories()
    context_parts.append({"type": "core", "content": core_memories})
    
    # 2. 根据 focus 动态选择活跃记忆
    active_memories = select_memories_by_focus(
        focus=active_context_config.focus,
        budget=budget.memory_allocation * budget.max_total,
        strategy="recency + relevance"
    )
    context_parts.append({"type": "active", "content": active_memories})
    
    # 3. 项目上下文
    project_context = load_project_context(active_context_config.focus.project_id)
    context_parts.append({"type": "project", "content": project_context})
    
    # 4. 会话历史
    session_history = load_recent_sessions(limit=3)
    context_parts.append({"type": "session", "content": session_history})
    
    return assemble_context(context_parts)
```

---

## 🧠 Memory 控制机制

### 1. Deduplication（去重）

```python
def deduplicate_candidates(candidates):
    """
    候选记忆去重
    """
    # 语义相似度检查
    for i, c1 in enumerate(candidates):
        for c2 in candidates[i+1:]:
            similarity = semantic_similarity(c1.content, c2.content)
            if similarity > 0.85:
                # 合并或删除
                merge_or_discard(c1, c2)
    
    # 检查与现有 memory 的重复
    for candidate in candidates:
        similar_memories = find_similar_memories(candidate.content, threshold=0.8)
        if similar_memories:
            candidate.status = "duplicate"
            candidate.duplicate_of = similar_memories[0].id
```

### 2. Versioning（版本化）

```yaml
# Memory 版本管理
context_id: "pref-001"
context_type: "preference"

# 版本历史
versions:
  - version: 1
    content: "喜欢使用 Python"
    created_at: "2026-01-01"
    status: "superseded"
  - version: 2
    content: "喜欢使用 Python，特别是 FastAPI 框架"
    created_at: "2026-03-01"
    status: "current"

# 替换关系
replaces: ["pref-001-v1"]
replaced_by: null
```

### 3. Compression（压缩）

```python
def compress_memories(memories):
    """
    多条相似记忆合并为一条原则
    """
    # 聚类相似记忆
    clusters = cluster_by_similarity(memories)
    
    for cluster in clusters:
        if len(cluster) > 3:
            # 生成更高层次的原则
            principle = generate_principle(cluster)
            create_memory(principle, type="principle")
            
            # 标记子记忆为已压缩
            for mem in cluster:
                mem.status = "compressed_into"
                mem.compressed_into = principle.id
```

### 4. TTL & Archival（过期处理）

```python
def memory_maintenance():
    """
    定期维护 memory
    """
    for memory in load_all_memories():
        age_days = (now - memory.created_at).days
        
        # 检查 TTL
        if memory.ttl_days and age_days > memory.ttl_days:
            if memory.access_count < 3:
                # 很少访问，归档
                archive_memory(memory)
            else:
                # 延长 TTL
                memory.ttl_days += 180
        
        # 标记过时决策
        if memory.type == "decision" and age_days > 180:
            memory.status = "review_needed"
            add_to_review_queue(memory)
```

### 5. Size Control（规模控制）

```yaml
# 配置在 config.yml
memory_limits:
  max_total: 1000               # 最多1000条记忆
  max_per_type:
    preference: 100
    decision: 200
    principle: 50
    fact: 500
    goal: 50
  
  # 超过限制时的处理
  overflow_strategy: "lru"      # LRU淘汰 / "archive"归档
  
  # 自动压缩
  auto_compress:
    enabled: true
    threshold: 5                # 5条相似记忆触发压缩
    min_age_days: 30
```

---

## 🔀 多 Agent 写入策略

### 方案：分支 + PR 模式

```
my-context-sync/
├── main                      # 受保护分支（人工审核）
├── agent/
│   ├── claude/              # Claude 的工作分支
│   ├── cursor/              # Cursor 的工作分支
│   └── gemini/              # Gemini 的工作分支
└── pr/                      # 合并请求
    ├── claude-2026-04-07-memory-update/
    └── cursor-2026-04-07-session-summary/
```

### 流程

```python
def agent_sync_workflow(agent_name, changes):
    """
    Agent 同步流程
    """
    # 1. Agent 在自己的分支工作
    branch = f"agent/{agent_name}"
    
    # 2. 创建候选记忆（不是直接写 memory）
    for change in changes:
        create_candidate_memory(change, source=agent_name)
    
    # 3. 提交到 agent 分支
    commit_to_branch(branch, changes)
    
    # 4. 创建 PR 到 main
    pr_id = create_pull_request(
        from_branch=branch,
        to_branch="main",
        title=f"[{agent_name}] Memory candidates from {date}"
    )
    
    # 5. 等待人工审核
    await_user_review(pr_id)
```

### Conflict Resolution

```yaml
# 冲突解决策略
conflict_resolution:
  # 相同 type + 相似 content
  duplicate_detection: true
  
  # 冲突时优先策略
  priority:
    - user_manual    # 人工编辑优先
    - claude         # 其次 Claude
    - cursor         # 其次 Cursor
    
  # 自动合并规则
  auto_merge:
    - condition: "no_overlap_in_tags"
      action: "merge"
    - condition: "confidence > 0.9 AND user_approved"
      action: "merge"
```

---

## 🛠️ CLI 保持兼容

### 现有命令升级

```bash
# === 保持不变 ===
auto-sync.py start              # 标记会话开始
auto-sync.py summary            # 生成会话总结（存入 logs/）
auto-sync.py push               # 推送到 GitHub
auto-sync.py pull               # 从 GitHub 拉取

# === 关键变化 ===
auto-sync.py suggest "描述"     # 生成 candidate_memory（不是 memory）
                                # 输出：等待审核的候选列表

# === 新增命令 ===
auto-sync.py review             # 审核待处理的 candidate
auto-sync.py review --auto      # 自动审核高置信度候选
auto-sync.py promote <id>       # 将 candidate 提升为 memory
auto-sync.py reject <id>        # 拒绝 candidate

auto-sync.py memory list        # 列出所有 semantic memory
auto-sync.py memory search      # 搜索 memory
auto-sync.py memory archive <id> # 归档 memory
auto-sync.py memory stats       # Memory 统计信息

auto-sync.py focus set <project> # 设置当前 focus
auto-sync.py focus get          # 获取当前 focus
auto-sync.py focus clear        # 清除 focus

auto-sync.py maintenance        # 运行 memory 维护（去重、归档、压缩）
```

### 配置升级

```yaml
# config.yml 扩展
version: "2.0.0"

# 保留现有配置
sync:
  mode: "hybrid"
  # ...

# 新增：Memory OS 配置
memory_os:
  # 审核配置
  review:
    auto_promote: true
    auto_promote_threshold:
      confidence: 0.9
      importance: 8
    require_manual_review: false    # true = 强制人工审核
    
  # Memory 控制
  control:
    max_memories: 1000
    deduplication: true
    compression: true
    ttl_enabled: true
    
  # Active Context
  active_context:
    auto_build: true                # 自动构建上下文
    token_budget: 8000
    core_memory_required: true
    
  # 多 Agent
  multi_agent:
    mode: "branch"                  # "branch" | "direct"
    require_pr: true
    auto_merge_high_confidence: true
```

---

## 📊 迁移路径

### Phase 1：目录结构调整（兼容）

```bash
# 自动迁移脚本
migrate-to-v2.py

# 1. 创建新目录结构
mkdir -p logs/{sessions,summaries,milestones}
mkdir -p candidate/{pending,approved,rejected}
mkdir -p memory/{core/{preferences,decisions,principles},active/{facts,goals},archive}

# 2. 迁移现有 memory
# 分析现有 memory，分类到 semantic types
# 未确认的降级为 candidate

# 3. 创建 active-context.yaml
```

### Phase 2：CLI 升级（向后兼容）

```bash
# suggest 命令行为变化
# v1: suggest -> 直接创建 memory
# v2: suggest -> 创建 candidate_memory -> 提示审核

# 添加 --legacy 选项保持旧行为
auto-sync.py suggest "描述" --legacy    # 直接创建 memory（不推荐）
```

### Phase 3：启用新特性

```bash
# 启用 Active Context
auto-sync.py focus set "项目A"

# 运行维护
auto-sync.py maintenance
```

---

## ✅ 实现检查清单

### 核心必须实现

- [ ] 1. 新目录结构创建
- [ ] 2. Candidate Memory schema 扩展
- [ ] 3. suggest → create_candidate 流程改造
- [ ] 4. review / promote 命令
- [ ] 5. active-context.yaml 机制
- [ ] 6. Context 构建器

### Memory 控制

- [ ] 7. Deduplication 机制
- [ ] 8. TTL & Archival
- [ ] 9. Size limits
- [ ] 10. Compression (可选)

### 增强功能

- [ ] 11. Multi-agent 分支支持
- [ ] 12. Memory 统计面板
- [ ] 13. 自动维护任务

---

## 📝 关键设计决策记录

### Decision 1：suggest 不直接写 memory

**问题**：suggest 直接创建 memory 会导致污染

**决策**：suggest 只创建 candidate_memory

**理由**：
- 强制审核流程
- AI 不能直接污染长期记忆
- 给用户控制权

### Decision 2：保留现有 CLI 命令

**问题**：升级是否破坏现有工作流？

**决策**：所有现有命令保留，行为微调

**理由**：
- summary 仍工作（但存入 logs/）
- push/pull 不变
- suggest 输出格式保持，只是内部创建 candidate

### Decision 3：Active Context 不强制

**问题**：是否要求必须使用 active-context.yaml？

**决策**：可选，默认启用

**理由**：
- 老用户可以忽略
- 新用户自动获得优化
- focus 为空时加载全部（向后兼容）

---

## 🚀 下一步行动

1. **创建 migrate-to-v2.py** - 自动迁移脚本
2. **升级 auto-sync.py** - 添加 candidate/review/focus 命令
3. **创建 context-builder.py** - Active Context 构建器
4. **测试迁移流程** - 确保现有数据不丢失
5. **更新文档** - README + SCHEMA + 迁移指南

---

*Design by: Claude + Jxy-yxJ*
*Version: 2.0.0-alpha*
*Date: 2026-04-07*
