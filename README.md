# oh-my-context -> Context Sync System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub](https://img.shields.io/badge/storage-GitHub-black.svg)](https://github.com)
[![Memory OS v2](https://img.shields.io/badge/Memory%20OS-v2.0-green.svg)](./MEMORY_OS_DESIGN.md)

自动上传你的context到github私有仓库，方便跨设备、模型、agent调用

> **一个关于"自我编译"的实验**
> 
> *"我是谁"可以不只是一个生物学问题，而可以是 `git clone`、`diff`、`merge` 的工程问题。*
>
> 这个项目的终极目标是：**把自己逐步编译成一个可加载的 context**。当有一天我下线了，希望还能：
> ```bash
> context pull me
> # 系统继续正常运行
> # 也许，还能提个 PR
> ```
> 

---

## 🆕 Memory OS v2.0

系统已升级为 **有纪律的 Memory OS**，核心变化：

| v1.x | v2.0 |
|------|------|
| 直接创建 memory | `suggest` → 创建 **candidate** → `review` → **promote** → memory |
| Memory 无限增长 | **三层架构** + **审核机制** + **TTL控制** |
| 所有内容都是 memory | Memory 只存 **稳定认知**（偏好/决策/原则/事实） |
| 无焦点管理 | **Active Context** 动态选择记忆 |

**v2.0 核心原则**：AI 不能直接写入 memory，必须经过审核。

## ✨ 核心特性

- **🔄 跨设备同步** - 多台机器无缝共享Context，工作流永不中断
- **🤖 跨模型兼容** - Claude/GPT/Gemini都能解析相同格式
- **👥 跨Agent共享** - 不同AI助手间传递上下文，接力完成任务
- **☁️ GitHub存储** - 版本控制 + 免费托管 + 全球访问
- **📝 Markdown优先** - 人类可读，LLM友好，永久保存
- **🛡️ 有纪律的Memory** - v2.0: 三层架构 + 审核机制，防止记忆污染
- **🎯 Active Context** - v2.0: 动态选择记忆，Token预算管理
- **🔧 Memory控制** - v2.0: 去重、TTL、压缩、大小限制

## 📋 系统要求

- Python 3.8+
- Git
- GitHub 账号
- (可选) GitHub CLI (`gh`)

## 🚀 快速开始

### 方式一：使用 GitHub CLI（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/context-sync.git
cd context-sync

# 2. 安装依赖
pip install click pyyaml gitpython

# 3. 创建数据仓库
gh repo create my-context-data --private --clone

# 4. 配置环境变量
setx CONTEXT_SYNC_REPO "C:\path\to\my-context-data"
setx CONTEXT_SYNC_SCRIPT "C:\path\to\context-sync\auto-sync.py"
```

### 方式二：手动设置

```bash
# 1. 克隆主仓库
git clone https://github.com/YOUR_USERNAME/context-sync.git

# 2. 在GitHub创建数据仓库（私有）
# 访问 https://github.com/new 创建

# 3. 克隆数据仓库
mkdir -p ~/context-sync-data
cd ~/context-sync-data
git init
git remote add origin https://github.com/YOUR_USERNAME/my-context-data.git

# 4. 创建目录结构
mkdir -p .context sessions memory projects tasks shared
```

## 📦 安装

### 依赖安装

```bash
# 必需依赖
pip install click pyyaml gitpython

# 可选依赖（用于高级功能）
pip install requests rich
```

### 添加到 PATH（推荐）

**Windows:**
```powershell
# 使用 PowerShell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";D:\Coding\context-sync-system", "User")
```

**macOS/Linux:**
```bash
# 添加到 .bashrc 或 .zshrc
export PATH="$PATH:/path/to/context-sync-system"
```

## ⚙️ 配置

创建配置文件 `~/.context-sync/config.yml`:

```yaml
version: "1.0.0"
user:
  id: "your-github-username"
  email: "your@email.com"
  
sync:
  mode: "hybrid"      # hybrid | auto | manual
  auto_push: true
  auto_pull: true
  
paths:
  repo: "~/context-sync-data"
  
features:
  milestone_detection: true
  session_summary: true
  smart_suggest: true
```

## 🎯 使用示例

### v2.0 Memory OS 命令

```bash
# ===== 核心工作流（重要）=====

# 1. 完成工作后，创建候选记忆
#    （不是直接写 memory，而是创建待审核的 candidate）
python auto-sync.py suggest "完成了登录功能，决定使用JWT认证"
# 输出: ✅ 已创建候选记忆 (类型: decision, 重要性: 9/10)
#       💡 运行 'auto-sync.py review' 进行审核

# 2. 审核候选记忆
python auto-sync.py review              # 交互式审核（推荐）
# 或
python auto-sync.py review --auto       # 自动通过高置信度候选

# 3. 审核通过后会自动：
#    - 创建 memory/core/decisions/decision-xxx.md
#    - 归档 candidate 到 candidate/approved/
#    - 推送到 GitHub

# ===== Active Context =====

# 设置当前焦点
python auto-sync.py focus set --project my-project --goal "实现用户认证"

# 查看当前焦点
python auto-sync.py focus get

# 构建上下文（根据焦点动态选择记忆）
python auto-sync.py context

# ===== Memory 查询 =====

# 列出所有语义记忆
python auto-sync.py memory list

# 显示统计信息
python auto-sync.py memory stats

# ===== 维护 =====

# 运行维护（去重、检查TTL、强制执行大小限制）
python auto-sync.py maintenance --dry-run   # 试运行
python auto-sync.py maintenance             # 执行维护

# ===== 基础命令 =====

# 推送/拉取
python auto-sync.py push
python auto-sync.py pull

# 生成会话总结
python auto-sync.py summary
```

### v1.x 兼容命令

```bash
# 创建Context记录
python auto-sync.py create "完成了用户登录功能" --type session --tags auth,feature

# 搜索历史Context
python auto-sync.py search "login"

# 同步到GitHub
python auto-sync.py push

# 拉取最新Context
python auto-sync.py pull
```

### 混合模式工作流（推荐）

```bash
# 1. 开始工作时
python auto-sync.py start

# 2. 完成重要工作时，获取智能建议
python auto-sync.py suggest "刚刚完成了数据库迁移"

# 3. 根据建议创建Context
python auto-sync.py create "完成了数据库迁移" --type memory --tags migration

# 4. 会话结束，自动生成总结
python auto-sync.py summary
```

## 📝 Context格式

```markdown
---
context_id: "550e8400-e29b-41d4-a716-446655440000"
context_type: "session"
version: "1.0.0"
created_at: "2026-04-07T10:30:00Z"
updated_at: "2026-04-07T11:45:00Z"
source:
  device_id: "device-hash"
  user_id: "username"
  agent_type: "claude-code"
  model: "claude-opus-4-6"
tags: ["project-x", "feature-y", "auth"]
relations:
  - type: "parent"
    context_id: "parent-uuid"
  - type: "related"
    context_id: "related-uuid"
---

# 会话内容

支持完整Markdown语法，包括：
- 代码块
- 列表
- 表格
- 链接

## 关键决策

- 使用JWT进行认证
- 数据库选择PostgreSQL
```

## 🔗 集成指南

### Claude Code 集成

在 `CLAUDE.md` 中添加:

```markdown
## Context Sync 集成

After completing SIGNIFICANT work:
- Run: python "D:\Coding\context-sync-system\auto-sync.py" suggest "{{summary}}"
- If suggested, run: python "D:\Coding\context-sync-system\auto-sync.py" create "{{description}}" --type memory

Before ending session:
- Run: python "D:\Coding\context-sync-system\auto-sync.py" summary
- Run: python "D:\Coding\context-sync-system\auto-sync.py" push

Before starting work:
- Run: python "D:\Coding\context-sync-system\auto-sync.py" pull
- Read relevant context from memory/
```

### 其他 Agent 集成

任何支持以下能力的Agent都可以使用：
- **读取**: Markdown + YAML frontmatter
- **写入**: 同样格式
- **同步**: git push/pull

## 📁 项目结构

```
context-sync-system/
├── auto-sync.py          # 主程序：自动化同步+智能检测
├── context-sync.py       # 核心CLI工具
├── scripts/
│   └── context-sync.py   # 兼容版本
├── README.md             # 本文件
├── LICENSE               # MIT许可证
├── SCHEMA.md            # Context Schema定义
├── IMPLEMENTATION.md    # 详细实现文档
├── HYBRID_GUIDE.md      # 混合模式指南
├── MILESTONE_GUIDE.md   # 里程碑检测指南
└── .gitignore           # Git忽略规则
```

## 📚 文档导航

### v2.0 Memory OS 文档

| 文档 | 内容 |
|------|------|
| [MEMORY_OS_DESIGN.md](./MEMORY_OS_DESIGN.md) | **核心设计文档** - 架构原则、流程设计、约束条件 |
| [MEMORY_OS_ARCHITECTURE.md](./MEMORY_OS_ARCHITECTURE.md) | **架构图** - 数据流、控制流、状态机可视化 |
| [MEMORY_OS_ROADMAP.md](./MEMORY_OS_ROADMAP.md) | **实现计划** - Phase 1-5 详细任务 |
| [SCHEMA_v2.md](./SCHEMA_v2.md) | **Schema v2.0** - 三层数据结构规范 |
| [QUICKSTART_v2.md](./QUICKSTART_v2.md) | **快速上手指南** - v2.0 工作流教程 |

### 通用文档

| 文档 | 内容 |
|------|------|
| [SCHEMA.md](./SCHEMA.md) | Context数据格式规范 (v1.0) |
| [OBSIDIAN_SYNC_GUIDE.md](./OBSIDIAN_SYNC_GUIDE.md) | Obsidian Vault 同步指南 |

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. **Fork** 本仓库
2. 创建你的 **Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** 你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. **Push** 到分支 (`git push origin feature/AmazingFeature`)
5. 发起 **Pull Request**

### 贡献领域

- 🐛 Bug修复
- ✨ 新功能
- 📖 文档改进
- 🌍 多语言支持
- 🧪 测试用例

## 🗺️ 路线图

- [ ] Web界面管理Context
- [ ] VS Code插件
- [ ] 自动冲突解决
- [ ] Context压缩和归档
- [ ] 团队协作功能
- [ ] AI驱动的Context摘要

## 📄 许可证

本项目基于 [MIT](LICENSE) 许可证开源。

## 💬 支持

- 📧 提交 [Issue](https://github.com/YOUR_USERNAME/context-sync/issues)
- 💡 查看 [Discussions](https://github.com/YOUR_USERNAME/context-sync/discussions)

## 🙏 致谢

感谢所有为跨Agent协作做出贡献的开发者！

---

**让AI助手拥有持久记忆，让工作流跨越设备边界。**
