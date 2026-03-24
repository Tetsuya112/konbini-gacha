"""
コンビニ商品スクレイパー
対象: セブン-イレブン / ローソン / ファミリーマート
カテゴリ: 弁当・おにぎり・パン・サンド・スイーツ・サラダ・惣菜・お菓子
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
import os
from datetime import datetime

# ──────────────────────────────────────────
# 設定
# ──────────────────────────────────────────
SLEEP_MIN = 6.0
SLEEP_MAX = 8.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# Render 永続ディスク(/data)があればそちら、なければローカルの ../data/
_data_dir = "/tmp" if os.environ.get("RENDER") else os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_PATH = os.path.join(_data_dir, "products.json")

# ──────────────────────────────────────────
# カテゴリ定義
# ──────────────────────────────────────────
SEVEN_CATEGORIES = [
    {"id": "onigiri",  "label": "おにぎり",   "url": "https://www.sej.co.jp/products/a/onigiri/"},
    {"id": "bento",    "label": "お弁当",     "url": "https://www.sej.co.jp/products/a/bento/"},
    {"id": "sandwich", "label": "サンドイッチ","url": "https://www.sej.co.jp/products/a/sandwich/"},
    {"id": "bread",    "label": "パン",       "url": "https://www.sej.co.jp/products/a/bread/"},
    {"id": "sweets",   "label": "スイーツ",   "url": "https://www.sej.co.jp/products/a/sweets/"},
    {"id": "salad",    "label": "サラダ",     "url": "https://www.sej.co.jp/products/a/salad/"},
    {"id": "souzai",   "label": "惣菜",       "url": "https://www.sej.co.jp/products/a/dailydish/"},
]

LAWSON_CATEGORIES = [
    {"id": "onigiri",  "label": "おにぎり",   "url": "https://www.lawson.co.jp/recommend/original/rice/"},
    {"id": "bento",    "label": "お弁当",     "url": "https://www.lawson.co.jp/recommend/original/bento/"},
    {"id": "sandwich", "label": "サンドイッチ","url": "https://www.lawson.co.jp/recommend/original/sandwich/"},
    {"id": "bread",    "label": "パン",       "url": "https://www.lawson.co.jp/recommend/original/bakery/"},
    {"id": "sweets",   "label": "スイーツ",   "url": "https://www.lawson.co.jp/recommend/original/dessert/"},
    {"id": "salad",    "label": "サラダ",     "url": "https://www.lawson.co.jp/recommend/original/salad/"},
    {"id": "souzai",   "label": "惣菜",       "url": "https://www.lawson.co.jp/recommend/original/select/osozai/"},
]

FAMIMA_CATEGORIES = [
    {"id": "onigiri",  "label": "おにぎり",   "url": "https://www.family.co.jp/goods/omusubi.html"},
    {"id": "bento",    "label": "お弁当",     "url": "https://www.family.co.jp/goods/obento.html"},
    {"id": "sandwich", "label": "サンドイッチ","url": "https://www.family.co.jp/goods/sandwich.html"},
    {"id": "bread",    "label": "パン",       "url": "https://www.family.co.jp/goods/bread.html"},
    {"id": "sweets",   "label": "スイーツ",   "url": "https://www.family.co.jp/goods/dessert.html"},
    {"id": "salad",    "label": "サラダ",     "url": "https://www.family.co.jp/goods/salad.html"},
    {"id": "souzai",   "label": "惣菜",       "url": "https://www.family.co.jp/goods/sidedishes.html"},
    {"id": "snack",    "label": "お菓子",     "url": "https://www.family.co.jp/goods/snack.html"},
]

# ──────────────────────────────────────────
# パーサー
# ──────────────────────────────────────────

def parse_seven(soup):
    """セブン: .list_inner > .item_ttl / .item_price"""
    items = []
    for card in soup.select(".list_inner"):
        name = card.select_one(".item_ttl")
        price_el = card.select_one(".item_price")
        if not name or not price_el:
            continue
        name = name.get_text(strip=True)
        m = re.match(r"^(\d+)円", price_el.get_text(strip=True))
        if not m:
            continue
        items.append({"name": name, "price": int(m.group(1))})
    return items


def parse_lawson(soup):
    """ローソン: .productList section li > .ttl / .price span"""
    items = []
    for li in soup.select(".productList section li"):
        name = li.select_one(".ttl")
        price_span = li.select(".price span")
        if not name or not price_span:
            continue
        name = name.get_text(strip=True)
        price_text = price_span[0].get_text(strip=True)
        m = re.match(r"^(\d+)$", price_text)
        if not m:
            continue
        items.append({"name": name, "price": int(m.group(1))})
    return items


def parse_famima(soup):
    """ファミマ: div.ly-mod-infoset3 > .ly-mod-infoset3-name / .ly-mod-infoset3-price"""
    items = []
    for card in soup.select("div.ly-mod-infoset3"):
        name = card.select_one(".ly-mod-infoset3-name")
        price_el = card.select_one(".ly-mod-infoset3-price")
        if not name or not price_el:
            continue
        name = name.get_text(strip=True)
        # 地域限定タグが名前に混じる場合を除去
        name = re.sub(r"^【[^】]+】", "", name).strip()
        m = re.match(r"^(\d+)円", price_el.get_text(strip=True))
        if not m:
            continue
        items.append({"name": name, "price": int(m.group(1))})
    return items


# ──────────────────────────────────────────
# 汎用フェッチ
# ──────────────────────────────────────────

def fetch(url, store_name):
    print(f"  → GET {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ⚠️  {store_name} fetch error: {e}")
        return None


def sleep():
    t = random.uniform(SLEEP_MIN, SLEEP_MAX)
    print(f"  💤 {t:.1f}秒待機...")
    time.sleep(t)


# ──────────────────────────────────────────
# ストア別スクレイプ
# ──────────────────────────────────────────

def scrape_store(store_id, store_label, categories, parser):
    print(f"\n{'='*50}")
    print(f"🏪 {store_label} スクレイピング開始")
    print(f"{'='*50}")
    result = {}
    for i, cat in enumerate(categories):
        print(f"\n[{i+1}/{len(categories)}] {cat['label']}")
        soup = fetch(cat["url"], store_label)
        if soup:
            items = parser(soup)
            result[cat["id"]] = {
                "label": cat["label"],
                "items": items,
            }
            print(f"  ✅ {len(items)}件取得")
        else:
            result[cat["id"]] = {"label": cat["label"], "items": []}
            print(f"  ❌ 取得失敗")

        # 最後のカテゴリ以外はスリープ
        if i < len(categories) - 1:
            sleep()

    return result


# ──────────────────────────────────────────
# メイン
# ──────────────────────────────────────────

def main():
    start = datetime.now()
    print(f"🚀 スクレイピング開始: {start.strftime('%Y-%m-%d %H:%M:%S')}")

    data = {
        "updated_at": start.isoformat(),
        "stores": {}
    }

    # セブン
    data["stores"]["seven"] = {
        "label": "セブン-イレブン",
        "categories": scrape_store("seven", "セブン-イレブン", SEVEN_CATEGORIES, parse_seven)
    }
    sleep()

    # ローソン
    data["stores"]["lawson"] = {
        "label": "ローソン",
        "categories": scrape_store("lawson", "ローソン", LAWSON_CATEGORIES, parse_lawson)
    }
    sleep()

    # ファミマ
    data["stores"]["famima"] = {
        "label": "ファミリーマート",
        "categories": scrape_store("famima", "ファミリーマート", FAMIMA_CATEGORIES, parse_famima)
    }

    # 保存
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    elapsed = (datetime.now() - start).seconds
    total = sum(
        len(cat["items"])
        for store in data["stores"].values()
        for cat in store["categories"].values()
    )
    print(f"\n{'='*50}")
    print(f"✅ 完了！ 合計 {total}件 / {elapsed}秒")
    print(f"💾 保存先: {OUTPUT_PATH}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
