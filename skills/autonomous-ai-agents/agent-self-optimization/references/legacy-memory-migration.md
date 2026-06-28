# Legacy MEMORY.md → Core YAML 迁移指南

一次性将传统 `~/.hermes/memories/MEMORY.md` 和 `USER.md` 中的知识蒸馏到 self-opt Core Memory YAML 架构。

## 背景

self-opt v2.0 的 Memory 架构以 `core/*.yaml`（facts/preferences/environment/patterns）为主要存储，传统 MEMORY.md/USER.md 标记为 deprecated。但两个文件之前积累了 39 条 MEMORY 条目和 10+ 条 USER 条目，需要一次性迁移。

## 迁移步骤

### Step 1：分析传统 memory

读取 MEMORY.md 和 USER.md，逐条识别分类：

| 分类 | 目标文件 | 示例 |
|------|----------|------|
| facts | `core/facts.yaml` | 用户身份、班型、项目信息、认证方式 |
| preferences | `core/preferences.yaml` | 只读约束、语言偏好、调用频率偏好 |
| environment | `core/environment.yaml` | NetBox URL、ELK 地址、provider 配置、端口号 |
| patterns | `core/patterns.yaml` | 排障流程、蒸馏规则、git commit 纪律、反馈层规则 |

### Step 2：去重检查

对比 core YAML 中已有条目，跳过已存在的（如"用户用中文"、"core Knowledge 需用户同意"）。

### Step 3：批量追加 YAML

```python
# 格式模板
def make_entry(prefix, num, content, conf='high'):
    return (
        f"- added: '{today}'\n"
        f"  confidence: {conf}\n"
        f"  content: {content}\n"
        f"  duplicate_count: 1\n"
        f"  id: {prefix}-{num}\n"
        f"  updated: '{today}'\n"
    )
```

使用 `execute_code` 脚本批量追加到各 YAML 文件末尾，注意从已有最大 ID + 1 开始。

### Step 4：替换传统文件

将 MEMORY.md 和 USER.md 替换为弃用标记：

```markdown
此文件已弃用。Memory 已蒸馏到 self-opt 三层架构：
  ~/.hermes/memories/core/facts.yaml       → 事实
  ~/.hermes/memories/core/preferences.yaml → 偏好
  ~/.hermes/memories/core/environment.yaml → 环境
  ~/.hermes/memories/core/patterns.yaml    → 模式/规则

运行 hermes self-opt memory --show 查看当前 Core Memory。
```

### Step 5：Git commit

```bash
cd ~/script/hermes-self-opt
git add -A
git commit -m "蒸馏传统memory到core YAML架构，弃用MEMORY.md/USER.md"
```

## 迁移结果（2026-06-29 实际执行）

| 目标文件 | 原条数 | 新增 | 总条数 |
|----------|--------|------|--------|
| facts.yaml | 11 | +7 | 18 |
| preferences.yaml | 10 | +8 | 18 |
| environment.yaml | 6 | +5 | 11 |
| patterns.yaml | 6 | +7 | 13 |

MEMORY.md: 3,059 → 355 bytes
USER.md: 1,918 → 252 bytes

## 注意事项

1. **core YAML 不自动注入会话**：迁移后 MEMORY.md 只剩弃用标记，agent 在下一次新会话中将丢失所有 memory 上下文。除非有 cron job 将 core YAML 编译回 MEMORY.md，或实现了自动注入机制。
2. **YAML 格式兼容**：确保 content 字段不含裸 `:` 或 YAML 特殊字符，必要时用引号包裹。
3. **不要删除旧的 MEMORY.md.bak 文件**：它们作为历史参考保留。
