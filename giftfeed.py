"""Build Ribbonwire's newest-first RSS feed for the Telegram channel publisher."""
import re
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

BASE = "https://giftfeed.fyi/"
NEW = BASE + "?sort=new"
OUTPUT = Path("ribbonwire.xml")
MEDIA = "http://search.yahoo.com/mrss/"
DC = "http://purl.org/dc/elements/1.1/"
ET.register_namespace("media", MEDIA)
ET.register_namespace("dc", DC)


def https(url):
    parts = urlsplit(url or "")
    return url if parts.scheme == "https" and parts.hostname and not parts.username else ""


def read_page(url):
    req = Request(url, headers={"User-Agent": "Ribbonwire RSS/1.0"})
    with urlopen(req, timeout=30) as response:
        page = BeautifulSoup(response.read(), "html.parser")
    cards = page.select(".article-card")
    if not cards:
        raise ValueError("No GiftFeed cards found")
    items = []
    for card in cards:
        title = card.select_one("a.article-title")
        discussion = card.select_one('a[href^="/article/"]')
        if not title or not discussion or not re.fullmatch(r"/article/\d+/?", discussion["href"]):
            raise ValueError("Unrecognized story card")
        item = ET.Element("item")
        link = https(title.get("href")) or urljoin(BASE, discussion["href"])
        ET.SubElement(item, "title").text = title.get_text(" ", strip=True)
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid", isPermaLink="true").text = urljoin(BASE, discussion["href"])
        for selector, tag in [(".pub-badge", f"{{{DC}}}creator"),(".article-description-feed", "description")]:
            value = card.select_one(selector)
            if value:
                ET.SubElement(item, tag).text = value.get_text(" ", strip=True)
        stamp = card.select_one("time[datetime]")
        if stamp:
            ET.SubElement(item, "pubDate").text = format_datetime(datetime.fromisoformat(stamp["datetime"].replace("Z","+00:00")))
        photo = card.select_one("img.thumbnail")
        if photo and (src := https(photo.get("src") or photo.get("data-src"))):
            ET.SubElement(item, f"{{{MEDIA}}}thumbnail", url=src)
        items.append(item)
    nxt = next((a for a in page.select("a[href]") if a.get_text(strip=True).startswith("Next")),None)
    next_url = urljoin(BASE,nxt["href"]) if nxt else ""
    if next_url and urlsplit(next_url).netloc != "giftfeed.fyi":
        raise ValueError("Unexpected pagination URL")
    return items,next_url


def main():
    old = ET.parse(OUTPUT).findall("channel/item") if OUTPUT.exists() else []
    old_head = old[0].findtext("guid") if old else ""
    url, visited, items = NEW, set(), {}
    while url:
        if url in visited:
            raise ValueError("Repeated pagination URL")
        visited.add(url)
        page, url = read_page(url)
        for item in page:
            items.setdefault(item.findtext("guid"),item)
        if not old_head or old_head in items:
            break
    for item in old:
        items.setdefault(item.findtext("guid"),item)
    root = ET.Element("rss",version="2.0")
    channel = ET.SubElement(root,"channel")
    for tag,value in [("title","Ribbonwire · GiftFeed"),("link",NEW),("description","Latest gift articles from GiftFeed.")]:
        ET.SubElement(channel,tag).text=value
    channel.extend(list(items.values())[:1000])
    ET.indent(root)
    temp = OUTPUT.with_suffix(".tmp")
    ET.ElementTree(root).write(temp,encoding="utf-8",xml_declaration=True)
    temp.replace(OUTPUT)
    print(f"Published {len(channel.findall('item'))} stories")


if __name__ == "__main__":
    main()
