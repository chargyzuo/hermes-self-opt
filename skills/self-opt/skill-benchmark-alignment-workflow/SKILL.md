---
name: skill-benchmark-alignment-workflow
description: 对齐Skill Benchmark与Router索引，并优化CJK匹配
triggers:
  - query: "检查Skill Router准确度"
  - query: "验证benchmark与router一致性"
---
# Skill Benchmark Alignment Workflow

## Steps
1. **提取所有已注册skill的frontmatter name**: `router.list_skills()` 并记录每个skill的`name`字段
2. **检查benchmark中的skill_name**: 确保`skill_router_benchmark.json`中的`expected_skill`与router返回的`name`完全一致（忽略大小写和连字符差异）
3. **修正不一致的条目**: 将benchmark中的skill_name改为router实际返回的name
4. **验证索引完整性**: 对比skill目录下的文件列表与router索引中的条目，确保无遗漏
5. **测试CJK匹配**: 对每个中文查询，确保router使用字符级匹配而非仅trigram，记录原始分数
6. **输出报告**: 计算准确率、召回率，列出所有失败案例及其原因