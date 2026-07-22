#!/usr/bin/env python3
"""Build one RSS 2.0 feed from 4TENLAB's public GitHub Pages Atom feeds."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

SOURCES = [
    ("AI시민연구소", "https://ai4tenlab.github.io/ai-citizen-lab-wiki/feed.xml"),
    ("뉴로시민", "https://ai4tenlab.github.io/everyday-neuroscience-lab/feed.xml"),
    ("정책과 시민", "https://ai4tenlab.github.io/korea-public-benefit-brief/feed.xml"),
    ("올웨더경제", "https://ai4tenlab.github.io/allweatheros/feed.xml"),
]
OUT = Path(__file__).resolve().parents[1] / "feed.xml"
ATOM = "{http://www.w3.org/2005/Atom}"


def text(node: ET.Element | None, default: str = "") -> str:
    return (node.text or default).strip() if node is not None else default


def atom_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def cdata(value: str) -> str:
    return "<![CDATA[" + value.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def fetch_items(source_name: str, url: str) -> list[dict]:
    request = Request(url, headers={"User-Agent": "4TENLAB-RSS-Aggregator/1.0"})
    with urlopen(request, timeout=40) as response:
        root = ET.fromstring(response.read())
    items = []
    for entry in root.findall(f"{ATOM}entry"):
        link = next((x.get("href") for x in entry.findall(f"{ATOM}link") if x.get("rel", "alternate") == "alternate" and x.get("href")), "") or ""
        if not link.startswith("https://ai4tenlab.github.io/"):
            continue
        updated = text(entry.find(f"{ATOM}updated"))
        content = text(entry.find(f"{ATOM}content")) or text(entry.find(f"{ATOM}summary"))
        items.append({
            "title": text(entry.find(f"{ATOM}title")),
            "link": link,
            "guid": text(entry.find(f"{ATOM}id"), link),
            "updated": atom_time(updated),
            "content": content,
            "source": source_name,
        })
    return items


def main() -> None:
    posts = [post for source, url in SOURCES for post in fetch_items(source, url)]
    posts.sort(key=lambda post: post["updated"], reverse=True)
    posts = posts[:50]
    now = datetime.now(timezone.utc)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        "  <channel>",
        "    <title>4TENLAB | Public Knowledge Feed</title>",
        "    <link>https://ai4tenlab.github.io/</link>",
        "    <description>4TENLAB의 AI, 뇌과학, 공공정책, 경제 공개 지식 채널 최신 글</description>",
        "    <language>ko</language>",
        f"    <lastBuildDate>{format_datetime(now, usegmt=True)}</lastBuildDate>",
    ]
    for post in posts:
        description = f"[{post['source']}] {post['content']}"
        lines.extend([
            "    <item>",
            f"      <title>{escape(post['title'])}</title>",
            f"      <link>{escape(post['link'])}</link>",
            f"      <guid isPermaLink=\"true\">{escape(post['link'])}</guid>",
            f"      <pubDate>{format_datetime(post['updated'], usegmt=True)}</pubDate>",
            f"      <category>{escape(post['source'])}</category>",
            f"      <description>{cdata(description)}</description>",
            f"      <content:encoded>{cdata(post['content'])}</content:encoded>",
            "    </item>",
        ])
    lines.extend(["  </channel>", "</rss>", ""])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} with {len(posts)} entries from {len(SOURCES)} sources")


if __name__ == "__main__":
    main()
