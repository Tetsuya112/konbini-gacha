"""スクレイパー - GitHub Gist保存版"""
import requests
from bs4 import BeautifulSoup
import json, time, random, re, os
from datetime import datetime

SLEEP_MIN = 6.0
SLEEP_MAX = 8.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# Gist設定（環境変数から）
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("GIST_ID", "")
GIST_FILE  = "konbini_products.json"

# ローカル保存先（開発用）
_data_dir = os.path.join(os.path.dirname(__file__), "../data")
LOCAL_PATH = os.path.join(_data_dir, "products.json")

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
        m = re.match(r"^(\d+)円", price_el.get_text(strip=True))
        if m: items.append({"name": name.get_text(strip=True), "price": int(m.group(1))})
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
        m = re.match(r"^(\d+)円", price_el.get_text(strip=True))
        if m: items.append({"name": n, "price": int(m.group(1))})
    return items

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

def scrape_store(store_id, store_label, categories, parser):
    print(f"\n{'='*50}\n🏪 {store_label}\n{'='*50}")
    result = {}
    for i, cat in enumerate(categories):
        print(f"\n[{i+1}/{len(categories)}] {cat['label']}")
        soup = fetch(cat["url"], store_label)
        if soup:
            items = parser(soup)
            result[cat["id"]] = {"label": cat["label"], "items": items}
            print(f"  ✅ {len(items)}件取得")
        else:
            result[cat["id"]] = {"label": cat["label"], "items": []}
        if i < len(categories) - 1:
            sleep()
    return result

def save_to_gist(data):
    """GitHub Gistにデータを保存"""
    if not GIST_TOKEN or not GIST_ID:
        print("⚠️  GIST_TOKEN or GIST_ID not set, skipping Gist save")
        return False
    try:
        payload = json.dumps({
            "files": {GIST_FILE: {"content": json.dumps(data, ensure_ascii=False)}}
        }).encode()
        req = requests.patch(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={
                "Authorization": f"token {GIST_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
            data=payload,
            timeout=15
        )
        req.raise_for_status()
        print(f"✅ Gist保存完了: https://gist.github.com/{GIST_ID}")
        return True
    except Exception as e:
        print(f"❌ Gist保存エラー: {e}")
        return False

def main():
    start = datetime.now()
    print(f"🚀 開始: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    data = {"updated_at": start.isoformat(), "stores": {}}
    data["stores"]["seven"]  = {"label": "セブン-イレブン",  "categories": scrape_store("seven",  "セブン-イレブン",  SEVEN_CATEGORIES,  parse_seven)}
    sleep()
    data["stores"]["lawson"] = {"label": "ローソン",         "categories": scrape_store("lawson", "ローソン",         LAWSON_CATEGORIES, parse_lawson)}
    sleep()
    data["stores"]["famima"] = {"label": "ファミリーマート",  "categories": scrape_store("famima", "ファミリーマート",  FAMIMA_CATEGORIES, parse_famima)}

    total = sum(len(c["items"]) for s in data["stores"].values() for c in s["categories"].values())
    print(f"\n✅ スクレイプ完了: {total}件")

    # Gistに保存（Render上）
    if GIST_TOKEN and GIST_ID:
        save_to_gist(data)
    # ローカルにも保存（開発用）
    os.makedirs(_data_dir, exist_ok=True)
    with open(LOCAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 ローカル保存: {LOCAL_PATH}")

if __name__ == "__main__":
    main()
