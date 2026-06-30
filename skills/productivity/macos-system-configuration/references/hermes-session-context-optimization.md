# Hermes CLI Session Context Size Optimization (macOS)

当用户反映 "新开 session 上下文太大" 或 token 消耗过高时使用的诊断-优化工作流。

## 诊断命令

```bash
# 查看初始 prompt 大小分解
hermes prompt-size

# 查看 enabled skills 列表
hermes skills list --enabled-only

# 查看 config 中的 platform_disabled 设置
python3 -c "
import yaml
cfg = yaml.safe_load(open('/Users/bytedance/.hermes/config.yaml'))
disabled = cfg.get('skills', {}).get('platform_disabled', {}).get('cli', [])
print(f'Disabled: {len(disabled)} skills')
"

# 扫描所有 SKILL.md 找出实际 enabled 的 skill
python3 -c "
from pathlib import Path
import yaml

cfg = yaml.safe_load(open('/Users/bytedance/.hermes/config.yaml'))
disabled = set(cfg.get('skills', {}).get('platform_disabled', {}).get('cli', []))

skill_dir = Path('/Users/bytedance/.hermes/skills')
enabled = []
for skill_file in sorted(skill_dir.rglob('SKILL.md')):
    lines = skill_file.read_text().split(chr(10))
    name = ''
    desc = ''
    in_fm = False
    for line in lines:
        if line.strip() == '---':
            in_fm = not in_fm
            continue
        if in_fm:
            if line.startswith('name:'):
                name = line.split(':', 1)[1].strip()
            elif line.startswith('description:'):
                desc = line.split(':', 1)[1].strip()
    if not name:
        continue
    if name not in disabled:
        enabled.append((name, desc))

for n, d in sorted(enabled):
    print(f'  {n}: {d}'  )
print(f'\nEnabled: {len(enabled)} skills')
"

# 查看当前 session 的 token 消耗（在日志中）
tail -20 ~/.hermes/logs/hermes.log | grep -E 'API call|in=|out=|total='
```

## prompt-size 输出的三个关键指标

```
System prompt total  :  28.9 KB (28,686 B)  ← 稳定的 prompt 部分
  skills index       :  17.5 KB (17,965 B)  ← 所有 enabled skill 的 name+description
  memory             :   0.9 KB  (  882 B)  ← 持久化 memory
Tool schemas         :  54.3 KB (55,559 B)  ← 所有工具的 JSON schema 定义（含 MCP servers）
```

## 常见优化手段

### 1. platform_disabled — 精简 Skills Index

在 `~/.hermes/config.yaml` 的 `skills.platform_disabled.cli` 列表中列出的 skill 不会被注入到 CLI 模式的 prompts 中。

```yaml
skills:
  platform_disabled:
    cli:
      - skill-name-1
      - skill-name-2
```

操作：
- 用 `hermes config edit` 直接编辑
- 所有不需要 CLI session 中自动加载的 skill 都加入
- 保留网络排障、GitHub、plan/spike、hermes-agent 等常用 skill
- 禁用整类：apple/creative/media/research/smart-home/social-media

效果：从 161 enabled → 28 enabled，skills index 从 ~17KB → ~6KB

### 2. 禁用 MCP Servers

MCP server 的 tool schema 会全部加载到 session 中，单个 MCP 的 tool 定义每增加一个 ~0.5KB-1KB。在 `~/.hermes/config.yaml` 中：

```yaml
mcp_servers:
  wechat:
    enabled: false  # ← 设 false 即可
  switch:
    enabled: false  # ← 设 false 即可
```

也可以用 CLI：
```bash
hermes config set mcp_servers.wechat.enabled false
hermes config set mcp_servers.switch.enabled false
```

效果：从 29 tools → 22 tools，tool schemas 从 ~54KB → ~47KB

### 3. 精简 Agent Guidance

```bash
hermes config set agent.task_completion_guidance false
hermes config set agent.parallel_tool_call_guidance false
hermes config set agent.coding_context ''
```

### 4. Personas 精简

保留最少的 personality 定义：
```yaml
agent:
  personalities:
    helpful: "You are a helpful, friendly AI assistant."
```

## 典型优化前后的对比

| 指标 | 优化前 | 优化后 | 减少 |
|------|-------|-------|------|
| System prompt | 28.9 KB | ~26 KB | ~3 KB |
| Tool schemas | 54.3 KB | ~47 KB | ~7 KB |
| 总初始化 | ~83 KB | ~73 KB | ~10 KB |
| 等价 tokens | ~21K | ~18K | ~3K tokens |

## 注意事项

- **修改 config 后需要 /reset 或新开 session 才能生效**
- `platform_disabled` 只影响 skills index 的注入，不影响 skill 的 installed 状态（下次需要时可随时 `/skill name` 加载）
- MCP server 可以随时重新启用：`hermes config set mcp_servers.switch.enabled true`
- `hermes skills config` 是交互式 UI，非 CLI 模式无法使用；用 `platform_disabled` 替代
- 无法通过 `hermes config set` 直接操作 `platform_disabled` 列表（数组结构），需要用 `hermes config edit` 编辑 YAML
