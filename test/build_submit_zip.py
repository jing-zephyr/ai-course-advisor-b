# -*- coding: utf-8 -*-
# 打提交附件包：测试单五个文件夹全量（排除 .env / 站点状态 / 缓存），输出到工作区根与桌面交付镜像
import os
import sys
import zipfile

SRC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TARGETS = [
    os.path.join(SRC, '软件与智能体赛道B级测试单_交付附件包.zip'),
    r'C:\Users\T\Desktop\20260822OPC order\软件与智能体赛道B级测试单_AI课程顾问_交付\软件与智能体赛道B级测试单_交付附件包.zip',
]
EXCLUDE_FILES = {'.env', '.netlify_site_id'}
EXCLUDE_DIRS = {'__pycache__'}


def add(zf, root):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn in EXCLUDE_FILES or fn.endswith('.zip'):
                continue
            full = os.path.join(dirpath, fn)
            arc = os.path.relpath(full, SRC)
            zf.write(full, arc)
            n += 1
    return n


for target in TARGETS:
    if os.path.exists(target):
        os.remove(target)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
        n = add(zf, SRC)
    print('zip:', target, n, 'files', os.path.getsize(target), 'bytes')
