const kb = require('../data/knowledge.json');

// 三区路由词：命中即限定检索范围，避免「夏令营费用」错配到「教师培训费用」
const ZONE_WORDS = {
  camp: ['夏令营', '学生', '孩子', '初中', '高中', '六年级', '高三', '线下班', '直播班', '走读', '住宿', '营员', '开营', '结营', '路演', '7天', '七天', '42课时', '作息', '熄灯', '物资', '北京班', '上海班', '早鸟'],
  teacher: ['教师', '老师', '师资培训', 'L1', 'L2', 'L3', '教研', '院校', '研修', '集训', '能力模型', '三级九维', '职称', '学校', '教育局', '学术委员会', '工作坊'],
  platform: ['平台', '会员', '接单', '订阅', '免费版', '基础版', '专业版', '大师', '企业合作', '工作室', '社区', '大赛', '智脑', '素养学院', 'OPC', '按量付费', '积分', '超级个体', 'B端'],
};

const STOP = new Set([...'的了是我你他她它这那有在和就不很还也您吗呢吧啊哦呀么什怎为于与及或而且被把给让到从向对哪些什么怎么多少']);

function bigrams(s) {
  const clean = s.replace(/[^一-龥a-zA-Z0-9]/g, '');
  const out = [];
  for (let i = 0; i < clean.length - 1; i++) {
    const b = clean.slice(i, i + 2);
    if (![...b].some((c) => STOP.has(c))) out.push(b);
  }
  return out;
}

// 路由：统计各区命中词数；唯一胜出则限定该区，否则全库检索（支持跨区对比提问）
function route(q) {
  const s = q.toLowerCase();
  const hits = {};
  for (const [zone, words] of Object.entries(ZONE_WORDS)) {
    hits[zone] = words.filter((w) => s.includes(w.toLowerCase())).length;
  }
  const sorted = Object.entries(hits).sort((a, b) => b[1] - a[1]);
  if (sorted[0][1] > 0 && sorted[1][1] === 0) return sorted[0][0];
  return 'all';
}

function scoreBlock(block, terms, query, idf) {
  const kw = (block.keywords || []).join('\n');
  let s = 0;
  for (const t of terms) {
    const w = idf[t] === undefined ? 1 : idf[t];
    if (block.title.includes(t)) s += 3 * w;
    else if (kw.includes(t)) s += 2 * w;
    else if (block.content.includes(t) || block.chapter.includes(t)) s += 1 * w;
  }
  // 关键词完整命中原句再加权：避免「教师培训L1学什么」里L1专属块输给公共概述块
  for (const k of block.keywords || []) {
    const w = idf[k] === undefined ? 1 : idf[k];
    if (k.length >= 2 && query.includes(k)) s += 3 * w;
  }
  return s;
}

function retrieve(query, topK = 5) {
  const r = route(query);
  const terms = bigrams(query);
  const pool = r === 'all' ? kb.blocks : kb.blocks.filter((b) => b.zone === r);
  // IDF-lite：在本区池中出现过半的词（如teacher区的「教师/培训」）不具区分度，降权
  const df = {};
  const vocab = [...new Set([...terms, ...pool.flatMap((b) => b.keywords || [])])];
  for (const t of vocab) {
    let n = 0;
    for (const b of pool) {
      if (b.title.includes(t) || (b.keywords || []).join('\n').includes(t) || b.content.includes(t)) n++;
    }
    df[t] = n;
  }
  const idf = {};
  for (const t of vocab) idf[t] = df[t] / pool.length > 0.5 ? 0.2 : 1;
  const items = [];
  for (const b of pool) {
    const s = scoreBlock(b, terms, query, idf);
    if (s > 0) items.push({ b, s });
  }
  items.sort((a, b) => b.s - a.s);
  return { route: r, chunks: items.slice(0, topK).map((x) => x.b) };
}

module.exports = { retrieve, route };
