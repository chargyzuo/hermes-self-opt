---
name: convert-docx-and-format-for-printing
description: 将 Markdown 或文本文件转换为 Word/PDF 格式，并调整排版以紧凑打印
prerequisites:
  - pandoc
  - python-docx
steps:
  - name: 复制文件副本
    command: cp <source_file> <destination_file>
  - name: 转换为 Word 文档
    command: pandoc <source_file> -o <output_file>.docx
  - name: 优化排版（缩小边距、字号、行距）
    script: |
      from docx import Document
      from docx.shared import Pt, Cm
      
      doc = Document('<output_file>.docx')
      
      # 设置页边距为 1cm
      for section in doc.sections:
        section.top_margin = Cm(1)
        section.bottom_margin = Cm(1)
        section.left_margin = Cm(1)
        section.right_margin = Cm(1)
      
      # 设置正文字号为 8pt，行距 1.0
      for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(8)
        paragraph.paragraph_format.line_spacing = 1.0
      
      # 设置标题字号为 14pt
      for paragraph in doc.paragraphs:
        if paragraph.style.name.startswith('Heading'):
            for run in paragraph.runs:
                run.font.size = Pt(14)
      
      # 设置表格单元格内边距和字号
      for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(8)
                # 调整单元格内边距
                cell.margin_top = Cm(0.035)
                cell.margin_bottom = Cm(0.035)
                cell.margin_left = Cm(0.035)
                cell.margin_right = Cm(0.035)
      
      doc.save('<output_file>.docx')
  - name: （可选）进一步压缩页数
    prompt: 询问用户是否需要缩小字号到 7pt 或改为两栏布局。