---
name: debug-context-length-discrepancy
description: 排查并修复 UI 显示 context length 额度与实际模型能力不一致的问题
---

# 排查上下文长度显示不一致

## 步骤
1. 确认用户当前 session 实际使用的模型名（通过检查运行日志中 `model` 或 `/model` 切换记录）
2. 检查 `config.yaml` 中 `model.context_length` 配置值（优先级最高）
3. 检查 `get_model_context_length()` 的执行路径：
   - 是否有 config override 传入
   - 是否命中 `model_metadata.py` 的硬编码表
   - 是否 fallback 到实际 API 的响应字段
4. 如果用户通过 `/model` 切换过模型，检查 `switch_model()` 中 `_config_context_length` 是否被清空
5. 确认硬编码表中模型 context length 是否与 API 实际返回一致
6. 若不一致，修改硬编码表或配置正确的 `context_length`
7. 修复切换模型时 context_length 的传递逻辑，确保新模型能正确获取真实窗口大小