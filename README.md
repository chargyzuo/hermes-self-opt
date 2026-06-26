# hermes-self-opt — Agent Self-Optimization Plugin for Hermes

Phase 1: Harvest → Mine → Gate-Lite

## Directory Structure

```
hermes-self-opt/
├── README.md
├── pyproject.toml
├── hermes_self_opt/
│   ├── __init__.py
│   ├── harvest.py      # Step 1: 从 Session DB 读取数据
│   ├── mine.py          # Step 2: LLM 提取三样东西
│   ├── gate.py          # Step 3: Gate-Lite 验证
│   ├── writer.py        # Step 4: 写入 Memory & Skills
│   ├── pipeline.py      # Step 5: 串联全流程
│   └── cli.py           # hermes self-opt 子命令
└── tests/
    └── test_harvest.py
```
