# Router 准确率诊断方法

通过 benchmark 数据系统诊断 skill router 准确率问题的方法论。

## 诊断流程

```python
# 1. 加载 benchmark
bench = json.loads(open('skill_router_benchmark.json').read())

# 2. 对每条 benchmark query 跑 query()
for skill_data in bench:
    for q in skill_data['queries']:
        results = query(q)  # router.query()

# 3. 分三类统计 miss
misses = {
    'no_results': [],      # score 全低于 MIN_SCORE → 无结果
    'wrong_match': [],     # 有结果但 top-1 不是期望 skill
    'cjk_confusion': [],   # CJK 匹配到了但相近 skill 混淆
}
```

## 常见根因

| 根因 | 占比 | 特征 |
|------|------|------|
| MIN_SCORE 太高 | ~65% | 短中文查询字符级重叠分加不上 0.3 |
| CJK 字符重叠混淆 | ~23% | 相近 skill description 共享关键词 |
| 误匹配 | ~12% | description 里碰巧有无关关键词 |

## 修复方向

1. **降 MIN_SCORE** — 从 0.3 → 0.15，大部分 NO RESULTS 会回来
2. **加 jieba** — 中文分词后词级匹配替代字符级重叠
3. **两者都做** — 双保险

## 验证方法

- 改完后跑全量 benchmark：`python3 -c "..." ` 输出 top-1 / top-3
- 对比改前改后 miss 分类变化
