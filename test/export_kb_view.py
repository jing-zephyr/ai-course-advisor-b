# -*- coding: utf-8 -*-
# 把 knowledge.json 导出为可阅读的 Markdown 知识库视图（01_知识库归档用）
import json
import os

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.dirname(os.path.dirname(APP))  # 测试单根目录
KB = json.load(open(os.path.join(APP, 'data', 'knowledge.json'), encoding='utf-8'))
blocks = KB['blocks'] if isinstance(KB, dict) else KB

ZONE_NAME = {'camp': '素材A 夏令营（2026暑期AI素养夏令营课程手册）',
             'teacher': '素材B 教师培训（初高中教师AI素养培训体系介绍）',
             'platform': '素材C OPC平台（OPC超级个体赋能平台产品白皮书）'}

lines = ['# 结构化知识库（共 %d 块）' % len(blocks), '',
         '> 本文件由 `02_系统/app/data/knowledge.json` 自动导出（test/export_kb_view.py），',
         '> 用于评审查阅知识库结构；系统运行时以 JSON 为准，两者内容一致。', '',
         '## 构建方法', '',
         '1. 三份素材 DOCX → 纯文本（保留章节标题层级），原文不改写；',
         '2. 按「章 → 节」人工划定切分点，每块 = 一个可独立回答问题的最小完整语义单元；',
         '3. 每块标注：ID / 分区（camp·teacher·platform）/ 来源文档 / 章节 / 标题 / 关键词 / 正文；',
         '4. 关键词覆盖同义问法（如「多少钱 / 费用 / 价格 / 早鸟」），供检索加权；',
         '5. 检索：分区路由 → 中文二元组切词 → 标题+3 / 关键词+2 / 正文+1 加权 → 区公共词 IDF-lite 降权。', '']

cur_zone = None
for b in blocks:
    if b['zone'] != cur_zone:
        cur_zone = b['zone']
        lines += ['', '---', '', '## ' + ZONE_NAME[cur_zone], '']
    lines += ['### %s %s' % (b['id'], b['title']), '',
              '- 来源：%s · %s' % (b['doc'], b['chapter']),
              '- 关键词：%s' % '、'.join(b['keywords']), '',
              b['content'], '']

out_path = os.path.join(OUT, '01_知识库', '结构化知识库_36块.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('written:', out_path, os.path.getsize(out_path), 'bytes')
