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
EXCLUDE_DIRS = {'__pycache__', '_K3交付版', '04_过程记录', '00_任务与素材'}  # _K3交付版是验证暂存区不重复入包；04_过程记录（排坑留痕与实拍截图）与00_任务与素材（赛题输入素材，平台方已有）按用户决策仅留本地，不入提交附件包


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
