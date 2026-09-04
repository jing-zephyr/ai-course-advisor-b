# -*- coding: utf-8 -*-
# 脱敏核查：sessions.json 中疑似手机号的数字是否实为时间戳字段
import json
import re
import sys

path = sys.argv[1]
raw = open(path, encoding='utf-8').read()

for m in list(re.finditer(r'1[3-9]\d{9}', raw))[:3]:
    s = max(0, m.start() - 30)
    print('命中上下文:', raw[s:m.end() + 15].replace('\n', ' '))

d = json.loads(raw)
sid = next(iter(d))
print('首会话结构字段:', list(d[sid].keys()))
msgs = d[sid].get('messages') or []
if msgs:
    print('消息字段:', list(msgs[0].keys()))
