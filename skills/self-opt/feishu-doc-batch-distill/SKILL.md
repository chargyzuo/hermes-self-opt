---
id: feishu-doc-batch-distill
name: 飞书文档批量蒸馏
version: 1.0.0
inputs:
  - doc_url: 飞书文档主目录链接
  - output_root: 输出根目录，默认 ~/.hermes/knowledge/normal
  - vendor_dirs: 厂商子目录列表
  - obsidian_manifest_path: Obsidian 已蒸馏文档清单路径
---

# 飞书文档批量蒸馏

## 步骤
1. **读取飞书主目录**：使用 lark-cli 获取文档内容，提取所有子文档链接（token）。
2. **去重与过滤**：从 Obsidian 已蒸馏文档清单中读取已处理 token，跳过；过滤无权限文档。
3. **分批并行处理**：按每批 10 个文档将剩余文档分组，使用子代理并行蒸馏。
4. **单个文档蒸馏**：
   - 读取飞书文档 Markdown 内容。
   - 解析标题、标签、现象、排查路径、根因、方案、操作、备注。
   - 按结构化模板生成 Markdown 文件，文件名为英文小写连字符 id。
   - 存入 `output_root/<vendor>/<id>.md`。
5. **更新已蒸馏清单**：将每个蒸馏成功的文档 token、标题、文件路径追加到 obsidian_manifest_path。
6. **验证**：统计总文件数、各目录文件数、跳过的文档数，输出汇总报告。