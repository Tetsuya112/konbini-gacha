"""
v1: 価格のみ版スクレイパー → Gist直接アップロード
所要時間: 約4〜5分

使い方:
  set GIST_TOKEN=ghp_xxxxxxxxxxxx
  python v1/scrape_and_upload.py
"""
import requests
from bs4 import BeautifulSoup
import json, time, random, re, os
from datetime import datetime

GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = "e3064a46d4f39092cee0138cbe8a7e6c"  # v1用（既存のGist）
GIST_FILE  = "konbini_products.json"

SLEEP_MIN = 6.0
SLEEP_MAX = 8.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

SEVEN_CATEGORIES = [
    {"id": "onigiri",  "label": "おにぎり",    "url": "https://www.sej.co.jp/products/a/onigiri/"},
    {"id": "bento",    "label": "お弁当",      "url": "https://www.sej.co.jp/products/a/bento/"},
    {"id": "sandwich", "label": "サンドイッチ", "url": "https://www.sej.co.jp/products/a/sandwich/"},
    {"id": "bread",    "label": "パン",        "url": "https://www.sej.co.jp/products/a/bread/"},
    {"id": "sweets",   "label": "スイーツ",    "url": "https://www.sej.co.jp/products/a/sweets/"},
    {"id": "salad",    "label": "サラダ",      "url": "https://www.sej.co.jp/products/a/salad/"},
    {"id": "souzai",   "label": "惣菜",        "url": "https://www.sej.co.jp/products/a/dailydish/"},
]
LAWSON_CATEGORIES = [
    {"id": "onigiri",  "label": "おにぎり",    "url": "https://www.lawson.co.jp/recommend/original/rice/"},
    {"id": "bento",    "label": "お弁当",      "url": "https://www.lawson.co.jp/recommend/original/bento/"},
    {"id": "sandwich", "label": "サンドイッチ", "url": "https://www.lawson.co.jp/recommend/original/sandwich/"},
    {"id": "bread",    "label": "パン",        "url": "https://www.lawson.co.jp/recommend/original/bakery/"},
    {"id": "sweets",   "label": "スイーツ",    "url": "https://www.lawson.co.jp/recommend/original/dessert/"},
    {"id": "salad",    "label": "サラダ",      "url": "https://www.lawson.co.jp/recommend/original/salad/"},
    {"id": "souzai",   "label": "惣菜",        "url": "https://www.lawson.co.jp/recommend/original/select/osozai/"},
]
FAMIMA_CATEGORIES = [
    {"id": "onigiri",  "label": "おにぎり",    "url": "https://www.family.co.jp/goods/omusubi.html"},
    {"id": "bento",    "label": "お弁当",      "url": "https://www.family.co.jp/goods/obento.html"},
    {"id": "sandwich", "label": "サンドイッチ", "url": "https://www.family.co.jp/goods/sandwich.html"},
    {"id": "bread",    "label": "パン",        "url": "https://www.family.co.jp/goods/bread.html"},
    {"id": "sweets",   "label": "スイーツ",    "url": "https://www.family.co.jp/goods/dessert.html"},
    {"id": "salad",    "label": "サラダ",      "url": "https://www.family.co.jp/goods/salad.html"},
    {"id": "souzai",   "label": "惣菜",        "url": "https://www.family.co.jp/goods/sidedishes.html"},
    {"id": "snack",    "label": "お菓子",      "url": "https://www.family.co.jp/goods/snack.html"},
]

def parse_seven(soup):
    items = []
    for card in soup.select(".list_inner"):
        name = card.select_one(".item_ttl")
        price_el = card.select_one(".item_price")
        if not name or not price_el: continue
        text = price_el.get_text(strip=True)
        m_tax  = re.search(r"税込([\d.]+)円", text)
        m_base = re.match(r"^(\d+)円", text)
        if m_tax:    items.append({"name": name.get_text(strip=True), "price": round(float(m_tax.group(1)))})
        elif m_base: items.append({"name": name.get_text(strip=True), "price": int(m_base.group(1))})
    return items

def parse_lawson(soup):
    items = []
    for li in soup.select(".productList section li"):
        name = li.select_one(".ttl")
        spans = li.select(".price span")
        if not name or not spans: continue
        m = re.match(r"^(\d+)$", spans[0].get_text(strip=True))
        if m: items.append({"name": name.get_text(strip=True), "price": int(m.group(1))})
    return items

def parse_famima(soup):
    items = []
    for card in soup.select("div.ly-mod-infoset3"):
        name = card.select_one(".ly-mod-infoset3-name")
        price_el = card.select_one(".ly-mod-infoset3-price")
        if not name or not price_el: continue
        n = re.sub(r"^【[^】]+】", "", name.get_text(strip=True)).strip()
        text = price_el.get_text(strip=True)
        m_tax  = re.search(r"税込(\d+)円", text)
        m_base = re.match(r"^(\d+)円", text)
        if m_tax:    items.append({"name": n, "price": int(m_tax.group(1))})
        elif m_base: items.append({"name": n, "price": int(m_base.group(1))})
    return items

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ⚠ {e}")
        return None

def sleep():
    t = random.uniform(SLEEP_MIN, SLEEP_MAX)
    print(f"  💤 {t:.1f}秒待機...")
    time.sleep(t)

def scrape_store(label, categories, parser):
    print(f"\n{'='*50}\n🏪 {label}\n{'='*50}")
    result = {}
    for i, cat in enumerate(categories):
        print(f"\n[{i+1}/{len(categories)}] {cat['label']}")
        soup = fetch(cat["url"])
        if soup:
            items = parser(soup)
            result[cat["id"]] = {"label": cat["label"], "items": items}
            print(f"  ✅ {len(items)}件")
        else:
            result[cat["id"]] = {"label": cat["label"], "items": []}
        if i < len(categories) - 1:
            sleep()
    return result

def save_to_gist(data):
    print("\n📤 Gistにアップロード中 (v1)...")
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        json={"files": {GIST_FILE: {"content": json.dumps(data, ensure_ascii=False)}}},
        timeout=15,
    )
    r.raise_for_status()
    print("✅ Gist保存完了 (v1)!")

def main():
    if not GIST_TOKEN:
        print("❌ GIST_TOKEN が設定されていません")
        print("   Windows: set GIST_TOKEN=ghp_xxxxxxxxxxxx")
        return
    start = datetime.now()
    print(f"🚀 v1 開始: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("⏱  所要時間の目安: 約4〜5分")
    data = {"updated_at": start.isoformat(), "stores": {}}
    data["stores"]["seven"]  = {"label": "セブン-イレブン",  "categories": scrape_store("セブン-イレブン",  SEVEN_CATEGORIES,  parse_seven)}
    sleep()
    data["stores"]["lawson"] = {"label": "ローソン",         "categories": scrape_store("ローソン",         LAWSON_CATEGORIES, parse_lawson)}
    sleep()
    data["stores"]["famima"] = {"label": "ファミリーマート",  "categories": scrape_store("ファミリーマート",  FAMIMA_CATEGORIES, parse_famima)}
    total = sum(len(c["items"]) for s in data["stores"].values() for c in s["categories"].values())
    print(f"\n✅ スクレイプ完了: {total}件")
    save_to_gist(data)
    print("\n🎉 完了！ https://konbini-gacha.onrender.com を確認してください")

if __name__ == "__main__":
    main()
