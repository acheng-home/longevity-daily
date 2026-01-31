#!/usr/bin/env python3
"""
Longevity and Biohacking Daily Report Generator
Automatically fetches latest news and sends formatted email report
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional

# Configuration
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "acheng@ifree8.com")
EMAIL_FROM = "Longevity Daily <daily@resend.dev>"

# Search queries for different categories
SEARCH_QUERIES = [
    {"query": "longevity research 2026 latest", "category": "longevity_research"},
    {"query": "Bryan Johnson Blueprint longevity", "category": "influencer"},
    {"query": "NMN NAD+ supplement study", "category": "supplements"},
    {"query": "rapamycin anti-aging clinical trial", "category": "research"},
    {"query": "biohacking trends 2026", "category": "biohacking"},
    {"query": "Huberman Lab podcast latest", "category": "podcast"},
    {"query": "Peter Attia longevity", "category": "podcast"},
    {"query": "Reddit biohackers longevity", "category": "community"},
]


def search_brave(query: str, count: int = 5) -> list:
    """Search using Brave Search API"""
    if not BRAVE_API_KEY:
        print(f"Warning: No Brave API key, skipping search for: {query}")
        return []

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": count,
        "freshness": "pd"  # Past day
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = []
        if "web" in data and "results" in data["web"]:
            for item in data["web"]["results"]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "age": item.get("age", "")
                })
        return results
    except Exception as e:
        print(f"Search error for '{query}': {e}")
        return []


def fetch_all_news() -> dict:
    """Fetch news from all categories"""
    all_results = {}

    for item in SEARCH_QUERIES:
        query = item["query"]
        category = item["category"]
        print(f"Searching: {query}")
        results = search_brave(query, count=5)
        all_results[category] = results

    return all_results


def generate_html_report(news_data: dict) -> str:
    """Generate HTML email content with clickable links"""

    # Get current date in Beijing timezone
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    date_str = now.strftime("%Y年%m月%d日")
    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_map[now.weekday()]

    # Build news items HTML
    def build_news_section(items: list, limit: int = 3) -> str:
        if not items:
            return "<p style='color:#999;font-size:13px;'>暂无最新内容</p>"

        html_parts = []
        for item in items[:limit]:
            title = item.get("title", "")
            url = item.get("url", "")
            desc = item.get("description", "")[:200]

            html_parts.append(f'''
<div style="background:#f9fafb;border-radius:8px;padding:15px;margin-bottom:12px;">
<h4 style="margin:0 0 8px 0;font-size:14px;">
<a href="{url}" target="_blank" style="color:#10b981;text-decoration:none;">{title} &rarr;</a>
</h4>
<p style="margin:0;color:#4b5563;font-size:13px;">{desc}</p>
<div style="background:#ecfdf5;border-radius:4px;padding:8px 12px;margin-top:10px;font-size:11px;word-break:break-all;">
<a href="{url}" style="color:#059669;">{url}</a>
</div>
</div>''')

        return "".join(html_parts)

    # Main HTML template
    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:#333;max-width:680px;margin:0 auto;padding:20px;background:#f5f5f5;">
<div style="background:#fff;border-radius:12px;padding:30px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">

<div style="text-align:center;border-bottom:2px solid #10b981;padding-bottom:20px;margin-bottom:25px;">
<h1 style="color:#10b981;margin:0;font-size:24px;">长寿与生物黑客日报</h1>
<div style="color:#666;font-size:14px;margin-top:5px;">{date_str} | {weekday}</div>
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">长寿研究前沿</div>
{build_news_section(news_data.get("longevity_research", []))}
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">补剂与NAD+研究</div>
{build_news_section(news_data.get("supplements", []))}
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">临床试验进展</div>
{build_news_section(news_data.get("research", []))}
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">生物黑客趋势</div>
{build_news_section(news_data.get("biohacking", []))}
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">KOL动态</div>
{build_news_section(news_data.get("influencer", []))}
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">播客推荐</div>
{build_news_section(news_data.get("podcast", []))}
</div>

<div style="margin-bottom:25px;">
<div style="color:#10b981;font-size:16px;font-weight:bold;border-left:4px solid #10b981;padding-left:12px;margin-bottom:15px;">社区热议</div>
{build_news_section(news_data.get("community", []))}
</div>

<div style="background:#fef3c7;border-radius:8px;padding:15px;margin:25px 0;">
<div style="color:#92400e;font-weight:bold;margin-bottom:8px;">今日实用建议</div>
<ul style="margin:0;padding-left:20px;color:#92400e;">
<li>关注睡眠质量，这是免费且最有效的长寿干预</li>
<li>保持规律运动，Zone 2有氧训练对心血管健康至关重要</li>
<li>合理补充营养，但不要过度依赖补剂</li>
</ul>
</div>

<div style="font-style:italic;color:#6b7280;text-align:center;padding:20px;border-top:1px solid #e5e7eb;margin-top:25px;">
"最好的长寿策略是那些经过时间验证的基础：睡眠、运动、营养和社交连接。"
</div>

<div style="text-align:center;color:#9ca3af;font-size:12px;margin-top:30px;padding-top:20px;border-top:1px solid #e5e7eb;">
<p><strong>长寿与生物黑客日报</strong></p>
<p>打破信息茧房 | 传递前沿健康知识</p>
<p>Curated by Your Longevity Broker</p>
<p style="margin-top:15px;font-size:11px;">
资源导航:
<a href="https://www.hubermanlab.com/" style="color:#10b981;">Huberman Lab</a> |
<a href="https://peterattiamd.com/podcast/" style="color:#10b981;">Peter Attia</a> |
<a href="https://blueprint.bryanjohnson.com/" style="color:#10b981;">Blueprint</a> |
<a href="https://www.reddit.com/r/longevity/" style="color:#10b981;">r/longevity</a> |
<a href="https://www.reddit.com/r/Biohackers/" style="color:#10b981;">r/Biohackers</a>
</p>
</div>

</div>
</body>
</html>'''

    return html


def send_email_resend(to_email: str, subject: str, html_content: str) -> bool:
    """Send email using Resend API"""
    if not RESEND_API_KEY:
        print("Error: No Resend API key configured")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        print(f"Email sent successfully! ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    """Main function to generate and send daily report"""
    print("=" * 50)
    print("Longevity Daily Report Generator")
    print("=" * 50)

    # Check required environment variables
    if not BRAVE_API_KEY:
        print("Warning: BRAVE_API_KEY not set, using fallback content")

    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY not set, cannot send email")
        return

    # Fetch news
    print("\n[1/3] Fetching latest news...")
    news_data = fetch_all_news()

    # Count results
    total_items = sum(len(v) for v in news_data.values())
    print(f"Found {total_items} news items across {len(news_data)} categories")

    # Generate HTML
    print("\n[2/3] Generating HTML report...")
    html_content = generate_html_report(news_data)

    # Get date for subject
    beijing_tz = timezone(timedelta(hours=8))
    now = datetime.now(beijing_tz)
    date_str = now.strftime("%Y年%m月%d日")
    subject = f"长寿与生物黑客日报 | {date_str}"

    # Send email
    print(f"\n[3/3] Sending email to {EMAIL_TO}...")
    success = send_email_resend(EMAIL_TO, subject, html_content)

    if success:
        print("\n" + "=" * 50)
        print("Daily report sent successfully!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("Failed to send daily report")
        print("=" * 50)
        exit(1)


if __name__ == "__main__":
    main()
