# Context Schema v2.0 - Memory OS

> 从 "增强笔记" 到 "有纪律的 Memory OS"

---

## 核心变化

### v1.0 → v2.0

| 特性 | v1.0 | v2.0 |
|------|------|------|
| 数据流 | 单层 (直接 memory) | 三层 (logs → candidate → memory) |
| Memory 定义 | "重要信息" | "稳定认知" (偏好/决策/原则/事实) |
| AI 写入 | 直接写入 | 只能创建 candidate |
| 审核流程 | 无 | review → promote |
| Memory 控制 | 无 | TTL/size/deduplication |
| Active Context | 无 | 动态选择记忆 |

---

## 三层数据结构

### Layer 1: LOGS (事件流)

```yaml
# session / summary / milestone / log
context_type: "session"
append_only: true
retention: "1 year"  # 可清理
```

**特点**:
- 高频写入
- 短期保留
- 不直接影响决策
- 用于提取 candidate

### Layer 2: CANDIDATE (待审核)

```yaml
context_type: "candidate_memory"
candidate_for: "preference" | "decision" | "principle" | "fact"

# 评分
importance_score: 8.5      # 0-10
confidence_score: 0.82     # 0-1

# 来源
extraction_method: "ai" | "rule"
source_session: "session-uuid"
proposed_at: "2026-04-07T10:30:00Z"

# 审核状态
review_status: "pending" | "approved" | "rejected"
reviewed_by: "user" | "auto"
reviewed_at: "2026-04-07T11:00:00Z"
```

**特点**:
- AI/规则从 logs 提取
- 必须经过审核才能进入 memory
- 可人工修改
- 审核后归档

### Layer 3: SEMANTIC MEMORY (长期认知)

```yaml
context_type: "preference" | "decision" | "principle" | "fact" | "goal"
memory_tier: "core" | "active" | "archived"

# 生命周期
ttl_days: 365
access_count: 42
last_accessed: "2026-04-07T10:00:00Z"

# 验证
confidence: 0.95
verified_by: "user" | "auto"
verified_at: "2026-04-07T10:00:00Z"

# 版本
replaces: ["old-memory-uuid"]
version: 2
```

**特点**:
- 稳定认知
- 影响未来决策
- 有生命周期管理
- 可版本化

---

## 类型详解

### RECORD 类 (事件流)

| 类型 | 用途 | 示例 |
|------|------|------|
| `session` | 对话记录 | 完整对话历史 |
| `summary` | 会话总结 | "本次完成了登录功能" |
| `milestone` | 里程碑 | "项目A第一阶段完成" |
| `log` | 执行日志 | 自动化操作记录 |

### CANDIDATE 类 (新增)

| 类型 | 用途 |
|------|------|
| `candidate_memory` | 待审核的候选记忆 |

### KNOWLEDGE 类 (语义记忆)

| 类型 | 定义 | 示例 | 有效期 |
|------|------|------|--------|
| `preference` | 稳定偏好 | "喜欢使用Python" | 长期 |
| `decision` | 已确认决策 | "使用JWT认证" | 6-12月审核 |
| `principle` | 可复用原则 | "代码简洁优先" | 长期 |
| `fact` | 稳定事实 | "API地址是xxx" | 长期/更新时 |
| `goal` | 长期目标 | "完成硕士申请" | 达成时归档 |

### PROJECT 类 (保持不变)

| 类型 | 用途 |
|------|------|
| `project` | 项目上下文 |
| `task` | 具体任务 |

---

## 核心流程

### 1. suggest → candidate

```
User: auto-sync.py suggest "完成了登录功能"

System:
  1. 分析当前工作
  2. 提取候选: "使用JWT认证" (decision)
  3. 评分: importance=8, confidence=0.85
  4. 创建: candidate/pending/candidate-xxx.md
  5. 提示: "发现1个候选，运行 review 审核"
```

### 2. review → promote

```
User: auto-sync.py review

System:
  显示 candidate:
    - 类型: decision
    - 重要性: 8/10
    - 置信度: 0.85
    - 内容: "使用JWT认证"

  User选择:
    [a]pprove -> 创建 memory/core/decisions/decision-xxx.md
    [r]eject  -> 移动到 candidate/rejected/
    [m]odify  -> 编辑后创建
    [s]kip    -> 保持 pending
```

### 3. auto-promote

```yaml
# 高置信度自动通过
auto_promote:
  enabled: true
  rules:
    - confidence > 0.9 AND importance > 8
    - type == "preference" AND confidence > 0.85
```

---

## Active Context 配置

```yaml
# .context/state/active-context.yaml

version: "2.0.0"
focus:
  type: "project"
  project_id: "auth-system"
  goal: "实现用户认证模块"

memory:
  # 必须加载
  core:
    - memory/core/preferences/*
    - memory/core/decisions/*
    - memory/core/principles/*
  
  # 动态选择
  active:
    pattern: "memory/active/**/*"
    filter:
      tags: ["auth", "security"]
      last_accessed_within: "30d"
  
  # 排除
  exclude:
    - memory/archive/**

token_budget:
  max_total: 8000
  memory_allocation: 0.4

context_build:
  order:
    - { type: "system", priority: 100 }
    - { type: "core_memory", priority: 90 }
    - { type: "active_memory", priority: 80, limit: 2000 }
    - { type: "project_context", priority: 70 }
    - { type: "session_history", priority: 60, limit: 1000 }
```

---

## Memory 控制机制

### Deduplication (去重)

```python
# 语义相似度 > 0.85 视为重复
def is_duplicate(candidate):
    for memory in existing_memories:
        if semantic_similarity(candidate, memory) > 0.85:
            return True
    return False
```

### TTL (生存期)

| 类型 | 默认 TTL | 处理策略 |
|------|---------|---------|
| preference | 永久 | 更新时版本化 |
| decision | 180天 | 过期审核 |
| principle | 永久 | 更新时版本化 |
| fact | 365天 | 过期归档 |
| goal | 达成时 | 自动归档 |

### Size Limits

```yaml
max_total: 1000
max_per_type:
  preference: 100
  decision: 200
  principle: 50
  fact: 500
  goal: 50

overflow_strategy: "lru"  # 或 "archive"
```

### Compression

```
多个相似 preference → 一条 principle
多条相关 decision → 一条原则性 memory
```

---

## CLI 命令对照

### v1 vs v2

| v1 命令 | v2 行为 | 变化 |
|---------|---------|------|
| `suggest` | 创建 candidate，提示审核 | ✅ 关键变化 |
| `create` | 直接创建 memory (需确认) | 可选 |
| `summary` | 生成并保存到 logs/summary | 路径变化 |
| `push/pull` | 保持不变 | - |

### v2 新增命令

```bash
# 审核
auto-sync.py review              # 交互式审核
auto-sync.py review --auto       # 自动审核高置信度
auto-sync.py promote <id>        # 手动提升
auto-sync.py reject <id>         # 手动拒绝

# Memory 管理
auto-sync.py memory list         # 列出所有 memory
auto-sync.py memory search       # 搜索 memory
auto-sync.py memory archive <id> # 归档 memory
auto-sync.py memory stats        # 统计信息

# Active Context
auto-sync.py focus set <project> # 设置当前 focus
auto-sync.py focus get           # 获取当前 focus
auto-sync.py focus clear         # 清除 focus

# 维护
auto-sync.py maintenance         # 运行维护任务
```

---

## 迁移路径

### Step 1: 结构迁移

```bash
# 运行迁移脚本
python scripts/migrate-v1-to-v2.py

# 做什么:
# 1. 创建新目录结构
# 2. 迁移现有 memory 到 semantic types
# 3. 移动 sessions 到 logs/
```

### Step 2: 配置升级

```yaml
# 更新 config.yml
version: "2.0.0"
memory_os:
  enabled: true
  # ... 新配置
```

### Step 3: 审核现有 memory

```bash
# 将现有 memory 转为 candidate 重新审核
# （可选，推荐）
```

---

## 向后兼容

### v1 数据

- 保留在 memory/user/（可选）
- 或迁移到新的分层结构

### v1 CLI

- `suggest` 输出格式保持
- `summary` 正常工作
- `push/pull` 不变

### 渐进式迁移

```yaml
# 配置中启用 v2
memory_os:
  enabled: true
  
  # v1 兼容模式
  compat_mode: true  # suggest 仍创建 memory（不推荐）
```

---

## 最佳实践

### Memory 写入准则

**✅ 应该写入 Memory**:
- 稳定偏好（"我喜欢Python"）
- 关键决策（"使用PostgreSQL"）
- 可复用原则（"DRY原则"）
- 重要事实（"API限制100req/s"）
- 长期目标（"申请TUD"）

**❌ 不应该写入 Memory**:
- 临时信息（"今天天气"）
- 会话细节（"刚才讨论的内容"）
- 未完成的想法（"可能可以用..."）
- 代码片段（存 logs/）
- 待办事项（存 tasks/）

### Workflow 推荐

```
1. 工作前: auto-sync.py pull
           auto-sync.py focus set <项目>

2. 工作中: （正常对话）

3. 完成时: auto-sync.py suggest "做了什么"
           （AI提取候选）
           
4. 审核:   auto-sync.py review
           （选择 approve/reject）
           
5. 结束:   auto-sync.py summary
           auto-sync.py maintenance
           auto-sync.py push
```

---

## 相关文档

- [MEMORY_OS_DESIGN.md](MEMORY_OS_DESIGN.md) - 详细设计
- [MEMORY_OS_ARCHITECTURE.md](MEMORY_OS_ARCHITECTURE.md) - 架构图
- [MEMORY_OS_ROADMAP.md](MEMORY_OS_ROADMAP.md) - 执行计划

---

*Schema Version: 2.0.0*
*Last Updated: 2026-04-07*
