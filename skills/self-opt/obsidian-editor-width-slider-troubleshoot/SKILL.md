---
name: obsidian-editor-width-slider-troubleshoot
description: 解决Obsidian中Editor Width Slider插件滑动按钮不生效的问题
steps:
  - name: 检查readableLineLength设置
    action: 在Obsidian设置 → 外观中，确保“Readable line length”开关为打开状态（true）。因为Slider通过修改--file-line-width变量工作，该变量仅在readableLineLength=true时生效。
  - name: 检查Slider插件配置
    action: 打开插件设置，查看sliderPercentage值，可调高默认值（如70）以获得更宽初始宽度。
  - name: 验证插件是否正常工作
    action: 重启Obsidian后拖动滑块，观察宽度是否变化。如果仍无效，继续下一步。
  - name: 检查主题冲突
    action: 如果使用Minimal等第三方主题，主题可能覆盖--file-line-width变量。可临时切换到默认主题测试。
  - name: 检查插件代码缺陷
    action: 检查插件代码中onload()是否主动调用了updateEditorStyle()。如果未调用，拖拽前不会写入CSS，导致滑块首次拖动后才生效。
  - name: 最终解决方案
    action: 创建CSS片段，在.obsidian/snippets/下新建.css文件，写入：
```css
.markdown-source-view.mod-cm6 .cm-content,
.markdown-reading-view .markdown-preview-view {
  max-width: none !important;
}
```
    然后在Obsidian设置 → 外观 → CSS片段中启用它。同时可以禁用Editor Width Slider插件避免冲突。
  - name: 验证生效
    action: 重启Obsidian，编辑器内容应填满整个面板宽度。
notes:
  - 使用CSS片段方案最可靠，不受插件和主题兼容性问题影响。
  - 如果希望保留自定义宽度而非全宽，可修改max-width为具体像素值。
