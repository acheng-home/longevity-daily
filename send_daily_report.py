#!/usr/bin/env python3
"""
Longevity & Biohacking Daily Report
数据源：Brave + Reddit + PubMed + EuropePMC + OpenAlex + S2 + HN + RSS
"""

import os, time, html as H, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import requests
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException, DetectorFactory

DetectorFactory.seed = 0

# ── 配置 ──────────────────────────────────────────────────────
BRAVE_KEY  = os.environ.get("BRAVE_API_KEY")
RESEND_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO   = os.environ.get("EMAIL_TO",   "acheng@ifree8.com")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Longevity Daily <onboarding@resend.dev>")
YEAR       = datetime.now().year

# ── 搜索分类 ──────────────────────────────────────────────────
QUERIES = [
    (f"longevity anti-aging research {YEAR}",             "长寿研究前沿"),
    ("NMN NAD rapamycin metformin supplement",             "补剂与临床研究"),
    ("biohacking health optimization quantified self",     "生物黑客趋势"),
    ("Huberman Peter Attia Bryan Johnson podcast",         "播客与KOL动态"),
    ("sleep optimization circadian rhythm longevity",      "睡眠与昼夜节律"),
    ("intermittent fasting autophagy caloric restriction", "禁食与自噬"),
    ("zone 2 cardio strength training longevity",          "运动科学"),
    ("metabolic health glucose insulin CGM",               "代谢健康"),
    ("gut microbiome probiotic health research",           "肠道微生物组"),
    ("longevity drug clinical trial senolytic",            "临床试验动态"),
    ("epigenetics biological age clock methylation",       "表观遗传与生物年龄"),
    ("health wearable oura whoop longevity tracking",      "健康科技与可穿戴"),
]

# ── Reddit（免费，无需Key） ────────────────────────────────────
REDDIT_SOURCES = [
    ("longevity",           "长寿研究前沿"),
    ("LifeExtension",       "长寿研究前沿"),
    ("Biohackers",          "生物黑客趋势"),
    ("fasting",             "禁食与自噬"),
    ("intermittentfasting", "禁食与自噬"),
    ("sleep",               "睡眠与昼夜节律"),
    ("nutrition",           "代谢健康"),
    ("running",             "运动科学"),
    # 播客与KOL动态
    ("HubermanLab",         "播客与KOL动态"),
    # 健康科技与可穿戴
    ("ouraring",            "健康科技与可穿戴"),
    ("whoop",               "健康科技与可穿戴"),
    ("quantifiedself",      "健康科技与可穿戴"),
    ("wearables",           "健康科技与可穿戴"),
]

# ── PubMed（免费，无需Key） ────────────────────────────────────
PUBMED_SOURCES = [
    ("longevity aging intervention",          "长寿研究前沿"),
    ("NAD NMN supplement aging",              "补剂与临床研究"),
    ("autophagy fasting caloric restriction", "禁食与自噬"),
    ("biological age epigenetic clock",       "表观遗传与生物年龄"),
    ("senolytic drug clinical trial aging",   "临床试验动态"),
    ("gut microbiome longevity health",       "肠道微生物组"),
]

# ── Europe PMC（覆盖PubMed+bioRxiv，免费，无需Key） ──────────
EUROPEPMC_SOURCES = [
    ("longevity aging hallmarks",              "长寿研究前沿"),
    ("NMN NAD rapamycin supplement clinical",  "补剂与临床研究"),
    ("epigenetics methylation clock aging",    "表观遗传与生物年龄"),
    ("senolytic senostatic clinical trial",    "临床试验动态"),
]

# ── OpenAlex（全量学术库，免费，无需Key） ─────────────────────
OPENALEX_SOURCES = [
    ("longevity anti-aging intervention",  "长寿研究前沿"),
    ("gut microbiome longevity disease",   "肠道微生物组"),
    ("circadian rhythm sleep longevity",   "睡眠与昼夜节律"),
    ("exercise VO2max longevity aging",    "运动科学"),
]

# ── Semantic Scholar（学术+AI摘要，免费，无需Key） ────────────
S2_SOURCES = [
    ("rapamycin mTOR aging mechanism",     "临床试验动态"),
    ("autophagy induction aging",          "禁食与自噬"),
]

# ── Hacker News（科技社区讨论，免费，无需Key） ────────────────
HN_SOURCES = [
    ("longevity biohacking aging",         "生物黑客趋势"),
    ("NMN rapamycin anti-aging",           "补剂与临床研究"),
    ("huberman attia podcast health",      "播客与KOL动态"),
    ("oura whoop health wearable",         "健康科技与可穿戴"),
]

# ── RSS 订阅（学术期刊+专业博客+播客+YouTube，免费，无需Key） ─
RSS_SOURCES = [
    # 学术期刊
    ("https://www.nature.com/nataging.rss",                                               "长寿研究前沿"),
    ("https://longevity.technology/feed/",                                                "长寿研究前沿"),
    ("https://onlinelibrary.wiley.com/action/showFeed?jc=14749726&type=etoc&feed=rss",   "长寿研究前沿"),
    ("https://www.cell.com/cell-metabolism/inprogress.rss",                               "代谢健康"),
    ("https://www.foundmyfitness.com/feed",                                               "补剂与临床研究"),
    # 播客 RSS（无需Key）
    ("https://feeds.megaphone.fm/hubermanlab",                                            "播客与KOL动态"),
    ("https://peterattiamd.com/feed/podcast",                                             "播客与KOL动态"),
    ("https://feeds.simplecast.com/bpvhNAV3",                                             "播客与KOL动态"),  # Lifespan w/ Sinclair
    # YouTube 频道 Atom Feed（无需Key，公开可用）
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UC2D2CMWXMOVWx7giW1n3LIg",    "播客与KOL动态"),  # Huberman Lab
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCkVLLl5bkCrHFsHMBWMNy4w",    "播客与KOL动态"),  # Peter Attia MD
    ("https://www.youtube.com/feeds/videos.xml?channel_id=UCmKfRbykvEutdcCpbMD4KeA",    "播客与KOL动态"),  # Bryan Johnson
    # 健康科技博客 RSS
    ("https://ouraring.com/blog/feed/",                                                   "健康科技与可穿戴"),
]

# ── 每日轮换建议（21条，按日期循环取3条） ────────────────────
_TIPS = [
    "睡眠是最强长寿干预，保持 7-9 小时高质量睡眠，优先于一切补剂",
    "每周 150 分钟 Zone 2 有氧运动，是心血管健康的黄金标准",
    "肌肉量是寿命的重要预测指标，每周至少 2 次力量训练",
    "定期检测 ApoB、空腹血糖、HbA1c 等代谢指标，数据驱动健康",
    "间歇性禁食（16:8）可激活自噬机制，但需根据个人情况调整",
    "减少超加工食品，专注于真实食物的营养密度",
    "社交连接对寿命的影响不亚于戒烟——孤独是隐形的长寿杀手",
    "每天晒 10-30 分钟自然光，有助于维持维生素 D 和昼夜节律",
    "冷暴露（冷水浴）可激活棕色脂肪，提升代谢弹性与抗压能力",
    "压力管理与冥想可降低皮质醇，直接延缓细胞端粒缩短",
    "睡前 2 小时减少蓝光暴露，保护褪黑素分泌节律",
    "高强度间歇训练（HIIT）每周 1-2 次，提升线粒体密度与 VO₂max",
    "内脏脂肪是炎症的核心驱动，腰臀比比体重更能预测代谢健康",
    "口腔健康与心血管疾病密切相关，认真对待每天的刷牙与牙线",
    "避免久坐，每 60 分钟起身活动 5 分钟，打断静态代谢损伤",
    "认知刺激（学习新技能、丰富社交）可延缓神经退化，保护大脑",
    "橄榄油多酚、槲皮素等植物化合物有助于激活长寿基因通路",
    "深度睡眠和 REM 质量优先于总时长，可穿戴设备帮你量化进展",
    "禁食期间保持电解质平衡（钠、钾、镁），避免禁食疲劳感",
    "定期检测生物年龄（表观遗传时钟），量化而非猜测健康进展",
    "正念饮食、细嚼慢咽，可显著降低餐后血糖峰值和胰岛素波动",
]

# ── 每日轮换名言（7条） ───────────────────────────────────────
_QUOTES = [
    "最好的长寿策略是那些经过时间验证的基础：睡眠、运动、营养和社交连接。",
    "你不需要活到 150 岁，你需要的是在 90 岁时依然充满活力地生活。",
    "衰老不是必然的退化，而是可以被科学干预的生物学过程。",
    "数据是健康最好的朋友，量化你的身体，才能真正了解它。",
    "最贵的补剂不如最基础的生活方式：好睡眠、规律运动、真实食物。",
    "预防永远优于治疗，今天的每一个健康决策都在改写你的未来。",
    "长寿不是终点，充满活力地活过每一天才是真正的目标。",
]

# ── 通用重试（指数退避） ───────────────────────────────────────
def retry(fn, *a, tries=3, base=5, **kw):
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except Exception as e:
            if i == tries - 1: raise
            wait = base * (2 ** i)
            print(f"  [重试 {i+1}/{tries}] {e}，等待 {wait}s…")
            time.sleep(wait)

# ── 翻译（带缓存） ────────────────────────────────────────────
@lru_cache(maxsize=512)
def translate(text: str) -> str:
    if not text.strip(): return text
    try:
        if detect(text).startswith("zh"): return text
    except LangDetectException:
        pass
    try:
        time.sleep(0.3)
        return GoogleTranslator(source="auto", target="zh-CN").translate(text) or text
    except Exception as e:
        print(f"  [翻译失败，保留原文] {e}")
        return text

# ── 数据源 1：Brave Search ────────────────────────────────────
def search_brave(query: str, count=5) -> list[dict]:
    if not BRAVE_KEY: return []
    def _req():
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_KEY},
            params={"q": query, "count": count, "freshness": "pw"},
            timeout=30,
        )
        if r.status_code == 429: raise RuntimeError("429 Rate Limited")
        if r.status_code >= 500: raise RuntimeError(f"Server Error {r.status_code}")
        r.raise_for_status()
        return [
            {"title": i.get("title") or "", "url": i.get("url") or "", "description": i.get("description") or ""}
            for i in r.json().get("web", {}).get("results", [])
        ]
    try:
        return retry(_req, tries=3, base=5)
    except Exception as e:
        print(f"  [Brave失败] {query}: {e}")
        return []

# ── 数据源 2：Reddit ──────────────────────────────────────────
def search_reddit(subreddit: str, count=5) -> list[dict]:
    try:
        r = requests.get(
            f"https://www.reddit.com/r/{subreddit}/hot.json",
            headers={"User-Agent": "LongevityDailyBot/1.0"},
            params={"limit": count + 3},
            timeout=15,
        )
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
        return [
            {
                "title": p["data"].get("title") or "",
                "url": p["data"].get("url") or f"https://reddit.com{p['data'].get('permalink','')}",
                "description": (p["data"].get("selftext") or "").strip()[:200] or p["data"].get("title", ""),
            }
            for p in posts if not p["data"].get("stickied")
        ][:count]
    except Exception as e:
        print(f"  [Reddit失败] r/{subreddit}: {e}")
        return []

# ── 数据源 3：PubMed ──────────────────────────────────────────
def search_pubmed(query: str, count=5) -> list[dict]:
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    try:
        r = requests.get(f"{BASE}/esearch.fcgi", params={
            "db": "pubmed", "term": query, "sort": "pub date",
            "retmax": count, "retmode": "json", "datetype": "pdat", "reldate": 30,
        }, timeout=15)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        r2 = requests.get(f"{BASE}/esummary.fcgi", params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "json",
        }, timeout=15)
        r2.raise_for_status()
        result = r2.json().get("result", {})
        return [
            {
                "title": result.get(pid, {}).get("title") or "",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                "description": f"PubMed | {result.get(pid,{}).get('source','')} | {result.get(pid,{}).get('pubdate','')[:7]}",
            }
            for pid in ids if result.get(pid, {}).get("title")
        ]
    except Exception as e:
        print(f"  [PubMed失败] {query}: {e}")
        return []

# ── 数据源 4：Europe PMC（覆盖PubMed + bioRxiv） ─────────────
def search_europepmc(query: str, count=5) -> list[dict]:
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    # 使用 FIRST_PDATE 语法内嵌日期过滤（比 fromDate 参数语义更准确，按发布日期而非入库日期过滤）
    dated_query = f"{query} FIRST_PDATE:[{from_date} TO *]"
    try:
        r = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": dated_query, "resultType": "lite",
                "pageSize": count, "format": "json",
                "sort": "P_PDATE_D desc",
            },
            timeout=15,
        )
        r.raise_for_status()
        results = r.json().get("resultList", {}).get("result", [])
        return [
            {
                "title": p.get("title") or "",
                "url": f"https://europepmc.org/article/{p.get('source','MED')}/{p.get('id','')}",
                "description": f"EuropePMC | {p.get('source','')} | {p.get('pubYear','')}",
            }
            for p in results if p.get("title")
        ]
    except Exception as e:
        print(f"  [EuropePMC失败] {query}: {e}")
        return []

# ── 数据源 5：OpenAlex（全量学术库） ─────────────────────────
def search_openalex(query: str, count=5) -> list[dict]:
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            "https://api.openalex.org/works",
            params={
                "search": query,
                "sort": "publication_date:desc",
                "per-page": count,
                "filter": f"from_publication_date:{from_date}",
                "mailto": "longevitydailybot@example.com",
            },
            timeout=15,
        )
        r.raise_for_status()
        works = r.json().get("results", [])
        return [
            {
                "title": w.get("title") or "",
                "url": (w.get("primary_location") or {}).get("landing_page_url")
                       or w.get("doi") or f"https://openalex.org/{w.get('id','').split('/')[-1]}",
                "description": f"OpenAlex | {w.get('publication_date','')[:7]} | 引用：{w.get('cited_by_count',0)}",
            }
            for w in works if w.get("title")
        ]
    except Exception as e:
        print(f"  [OpenAlex失败] {query}: {e}")
        return []

# ── 数据源 6：Semantic Scholar（AI摘要学术搜索） ──────────────
def search_s2(query: str, count=5) -> list[dict]:
    try:
        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query, "limit": count,
                "fields": "title,url,abstract,publicationDate",
                "sort": "publicationDate:desc",
            },
            headers={"User-Agent": "LongevityDailyBot/1.0"},
            timeout=15,
        )
        r.raise_for_status()
        papers = r.json().get("data", [])
        return [
            {
                "title": p.get("title") or "",
                "url": p.get("url") or f"https://www.semanticscholar.org/paper/{p.get('paperId','')}",
                "description": (p.get("abstract") or "")[:200],
            }
            for p in papers if p.get("title")
        ]
    except Exception as e:
        print(f"  [S2失败] {query}: {e}")
        return []

# ── 数据源 7：Hacker News（科技社区） ────────────────────────
def search_hn(query: str, count=5) -> list[dict]:
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "tags": "story", "hitsPerPage": count},
            timeout=15,
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
        return [
            {
                "title": h.get("title") or "",
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}",
                "description": f"HN讨论 | 评论：{h.get('num_comments',0)} | 热度：{h.get('points',0)}",
            }
            for h in hits if h.get("title")
        ]
    except Exception as e:
        print(f"  [HN失败] {query}: {e}")
        return []

# ── 数据源 8：RSS 订阅（学术期刊/专业博客） ──────────────────
def search_rss(url: str, count=5) -> list[dict]:
    try:
        r = requests.get(url, headers={"User-Agent": "LongevityDailyBot/1.0"}, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        # RSS 2.0
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            desc  = (item.findtext("description") or "").strip()[:200]
            if title and link:
                items.append({"title": title, "url": link, "description": desc})
        # Atom
        if not items:
            ns = "http://www.w3.org/2005/Atom"
            for entry in root.iter(f"{{{ns}}}entry"):
                title = (entry.findtext(f"{{{ns}}}title") or "").strip()
                # 优先取 rel="alternate" 的文章链接，避免取到 rel="self" 的 feed URL
                link = ""
                for lel in entry.findall(f"{{{ns}}}link"):
                    rel  = lel.get("rel", "alternate")
                    href = lel.get("href", "")
                    if rel == "alternate" and href:
                        link = href
                        break
                if not link:
                    lel = entry.find(f"{{{ns}}}link")
                    link = lel.get("href", "") if lel is not None else ""
                summary = (entry.findtext(f"{{{ns}}}summary") or "").strip()[:200]
                if title and link:
                    items.append({"title": title, "url": link, "description": summary})
        return items[:count]
    except Exception as e:
        print(f"  [RSS失败] {url.split('/')[2]}: {e}")
        return []

# ── 八源并发抓取 + 去重 + 翻译 ───────────────────────────────
def fetch_all() -> list[tuple[str, list]]:
    order  = [label for _, label in QUERIES]
    bucket = {label: [] for label in order}

    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {}
        for q, label in QUERIES:
            futs[ex.submit(search_brave, q)] = label
        for sub, label in REDDIT_SOURCES:
            if label in bucket: futs[ex.submit(search_reddit, sub)] = label
        for q, label in PUBMED_SOURCES:
            if label in bucket: futs[ex.submit(search_pubmed, q)] = label
        for q, label in EUROPEPMC_SOURCES:
            if label in bucket: futs[ex.submit(search_europepmc, q)] = label
        for q, label in OPENALEX_SOURCES:
            if label in bucket: futs[ex.submit(search_openalex, q)] = label
        for q, label in S2_SOURCES:
            if label in bucket: futs[ex.submit(search_s2, q)] = label
        for q, label in HN_SOURCES:
            if label in bucket: futs[ex.submit(search_hn, q)] = label
        for url, label in RSS_SOURCES:
            if label in bucket: futs[ex.submit(search_rss, url)] = label

        for f in as_completed(futs):
            label = futs[f]
            try:
                items = f.result()
            except Exception as e:
                print(f"  [worker异常] {label}: {e}")
                items = []
            bucket[label].extend(items)
            if items:
                print(f"  ✓ {label}：+{len(items)} 条")

    # 按URL去重，每分类最多8条
    for label in bucket:
        seen, deduped = set(), []
        for item in bucket[label]:
            if item["url"] not in seen:
                seen.add(item["url"])
                deduped.append(item)
        bucket[label] = deduped[:8]

    # 并发翻译（限3线程）
    def tr(item):
        return {**item, "title": translate(item["title"]), "description": translate(item["description"])}

    with ThreadPoolExecutor(max_workers=3) as ex:
        for label in bucket:
            bucket[label] = list(ex.map(tr, bucket[label]))

    return [(label, bucket[label]) for label in order]

# ── HTML 生成 ─────────────────────────────────────────────────
esc  = H.escape
surl = lambda u: str(u).replace('"', "%22")
clip = lambda t: esc(t[:200] + ("…" if len(t) > 200 else ""))

_CARD = (
    '<div style="background:#f9fafb;border-radius:8px;padding:15px;margin-bottom:12px;">'
    '<h4 style="margin:0 0 8px 0;font-size:14px;">'
    '<a href="{h}" target="_blank" style="color:#10b981;text-decoration:none;">{title} &rarr;</a>'
    '</h4><p style="margin:0;color:#4b5563;font-size:13px;">{desc}</p>'
    '<div style="background:#ecfdf5;border-radius:4px;padding:8px 12px;margin-top:10px;'
    'font-size:11px;word-break:break-all;">'
    '<a href="{h}" style="color:#059669;">{disp}</a></div></div>'
)

def cards(items, lim=4):
    if not items: return "<p style='color:#999;font-size:13px;'>暂无最新内容</p>"
    return "".join(
        _CARD.format(h=surl(i["url"]), title=esc(i.get("title") or "（无标题）"),
                     desc=clip(i.get("description") or ""), disp=esc(i["url"]))
        for i in items[:lim]
    )

def section(label, items):
    return (
        '<div style="margin-bottom:25px;">'
        f'<div style="color:#10b981;font-size:16px;font-weight:bold;'
        f'border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">{label}</div>'
        f'{cards(items)}</div>'
    )

def build_html(sections):
    tz      = timezone(timedelta(hours=8))
    now     = datetime.now(tz)
    date    = now.strftime("%Y年%m月%d日")
    week    = "一二三四五六日"[now.weekday()]
    day_idx = now.timetuple().tm_yday

    tips      = [_TIPS[(day_idx + i) % len(_TIPS)] for i in range(3)]
    quote     = _QUOTES[day_idx % len(_QUOTES)]
    tips_html = "".join(f"<li>{t}</li>" for t in tips)
    body      = "".join(section(l, i) for l, i in sections)

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#333;max-width:680px;margin:0 auto;padding:20px;background:#f5f5f5;">
<div style="background:#fff;border-radius:12px;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,.1);">
<div style="text-align:center;border-bottom:2px solid #10b981;padding-bottom:20px;margin-bottom:25px;">
<h1 style="color:#10b981;margin:0;font-size:24px;">长寿与生物黑客日报</h1>
<div style="color:#666;font-size:14px;margin-top:5px;">{date} | 星期{week}</div></div>
{body}
<div style="background:#fef3c7;border-radius:8px;padding:15px;margin:25px 0;">
<div style="color:#92400e;font-weight:bold;margin-bottom:8px;">今日实用建议</div>
<ul style="margin:0;padding-left:20px;color:#92400e;">{tips_html}</ul></div>
<div style="font-style:italic;color:#6b7280;text-align:center;padding:20px;border-top:1px solid #e5e7eb;margin-top:25px;">
"{quote}"</div>
<div style="text-align:center;color:#9ca3af;font-size:12px;margin-top:30px;padding-top:20px;border-top:1px solid #e5e7eb;">
<p><strong>长寿与生物黑客日报</strong></p>
<p>打破信息茧房 | 传递前沿健康知识 | 每日精选长寿资讯</p>
<p style="font-size:11px;">
<a href="https://www.hubermanlab.com/" style="color:#10b981;">胡博曼实验室</a> |
<a href="https://peterattiamd.com/podcast/" style="color:#10b981;">彼得·阿提亚</a> |
<a href="https://blueprint.bryanjohnson.com/" style="color:#10b981;">蓝图计划</a> |
<a href="https://www.reddit.com/r/longevity/" style="color:#10b981;">长寿社区</a> |
<a href="https://www.reddit.com/r/Biohackers/" style="color:#10b981;">生物黑客社区</a> |
<a href="https://pubmed.ncbi.nlm.nih.gov/" style="color:#10b981;">PubMed文献库</a> |
<a href="https://openalex.org/" style="color:#10b981;">OpenAlex学术库</a>
</p></div></div></body></html>"""

# ── 发送邮件 ──────────────────────────────────────────────────
def send(subject: str, html: str) -> bool:
    if not RESEND_KEY:
        print("错误：未配置 RESEND_API_KEY"); return False
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            json={"from": EMAIL_FROM, "to": [EMAIL_TO], "subject": subject, "html": html},
            timeout=30,
        )
        if not r.ok: print(f"  [错误] {r.status_code}: {r.text}")
        r.raise_for_status()
        print(f"  ✅ 发送成功！ID: {r.json().get('id')}")
        return True
    except Exception as e:
        print(f"  ❌ 发送失败：{e}"); return False

# ── 主流程 ────────────────────────────────────────────────────
def main():
    sep = "─" * 50
    print(f"{sep}\n  Longevity Daily Report  |  {YEAR}\n{sep}")
    print(f"  TO: {EMAIL_TO}\n  FROM: {EMAIL_FROM}")

    if not RESEND_KEY:
        print("错误：RESEND_API_KEY 未配置，退出"); exit(1)

    print(f"\n[1/3] 八源并发抓取 + 翻译…")
    sections = fetch_all()
    print(f"  共 {sum(len(i) for _,i in sections)} 条")

    print(f"\n[2/3] 生成 HTML…")
    html = build_html(sections)

    now     = datetime.now(timezone(timedelta(hours=8)))
    subject = f"长寿与生物黑客日报 | {now.strftime('%Y年%m月%d日')}"

    print(f"\n[3/3] 发送至 {EMAIL_TO}…")
    exit(0 if send(subject, html) else 1)

if __name__ == "__main__":
    main()
