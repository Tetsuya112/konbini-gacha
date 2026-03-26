"""
ローカル実行用スクレイパー → Gist直接アップロード
カロリー・PFC（タンパク質/脂質/炭水化物）対応版

使い方:
  set GIST_TOKEN=ghp_xxxxxxxxxxxx   (Windows)
  export GIST_TOKEN=ghp_xxxxxxxxxxxx (Mac/Linux)
  python scrape_and_upload.py

所要時間: 約2〜2.5時間（詳細ページ巡回あり）
"""

import requests
from bs4 import BeautifulSoup
import json, time, random, re, os
from datetime import datetime

# ── 設定 ──────────────────────────────────
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("GIST_ID_V2", "")  # v2専用GistのID
GIST_FILE  = "konbini_products_v2.json"
# ─────────────────────────────────────────

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

# ══════════════════════════════════════════
# カテゴリ定義
# ══════════════════════════════════════════

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

# ══════════════════════════════════════════
# フェッチ共通
# ══════════════════════════════════════════

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ⚠  fetch error: {e}")
        return None

def sleep():
    t = random.uniform(SLEEP_MIN, SLEEP_MAX)
    print(f"  💤 {t:.1f}秒待機...")
    time.sleep(t)

def to_float(s):
    """文字列から数値を抽出 ('4.2g' → 4.2)"""
    try:
        return float(re.search(r"[\d.]+", s).group())
    except Exception:
        return None

# ══════════════════════════════════════════
# セブン
# ══════════════════════════════════════════

def parse_seven_nutrition(soup):
    """
    詳細ページの td に全栄養情報が1行で入っている:
    "熱量：252kcal、たんぱく質：4.2g、脂質：8.9g、炭水化物：39.6g..."
    """
    result = {}
    for td in soup.select("td"):
        text = td.get_text(strip=True)
        if "kcal" not in text or "たんぱく質" not in text:
            continue
        m_kcal    = re.search(r"熱量[：:]([\d.]+)kcal", text)
        m_protein = re.search(r"たんぱく質[：:]([\d.]+)g", text)
        m_fat     = re.search(r"脂質[：:]([\d.]+)g", text)
        m_carbs   = re.search(r"炭水化物[：:]([\d.]+)g", text)
        if m_kcal:
            result["kcal"]    = round(float(m_kcal.group(1)))
            result["protein"] = to_float(m_protein.group(1)) if m_protein else None
            result["fat"]     = to_float(m_fat.group(1))     if m_fat     else None
            result["carbs"]   = to_float(m_carbs.group(1))   if m_carbs   else None
        break
    return result

def scrape_seven(categories):
    print(f"\n{'='*50}\n🏪 セブン-イレブン\n{'='*50}")
    result = {}
    for ci, cat in enumerate(categories):
        print(f"\n[カテゴリ {ci+1}/{len(categories)}] {cat['label']}")
        soup = fetch(cat["url"])
        if not soup:
            result[cat["id"]] = {"label": cat["label"], "items": []}
            continue

        # 一覧から商品名・価格・詳細URLを取得
        raw_items = []
        seen_urls = set()
        for card in soup.select(".list_inner"):
            name_el    = card.select_one(".item_ttl")
            price_el   = card.select_one(".item_price")
            link_el    = card.select_one("a[href*='/products/a/item/']")
            if not name_el or not price_el:
                continue
            text = price_el.get_text(strip=True)
            m_tax  = re.search(r"税込([\d.]+)円", text)
            m_base = re.match(r"^(\d+)円", text)
            price = round(float(m_tax.group(1))) if m_tax else (int(m_base.group(1)) if m_base else None)
            if price is None:
                continue
            detail_url = link_el["href"] if link_el else None
            if detail_url and detail_url in seen_urls:
                continue
            if detail_url:
                seen_urls.add(detail_url)
            raw_items.append({
                "name": name_el.get_text(strip=True),
                "price": price,
                "detail_url": detail_url,
            })

        print(f"  一覧取得: {len(raw_items)}件 → 詳細ページを巡回します")

        items = []
        for i, item in enumerate(raw_items):
            nutrition = {}
            if item["detail_url"]:
                sleep()
                detail_soup = fetch(item["detail_url"])
                if detail_soup:
                    nutrition = parse_seven_nutrition(detail_soup)
                    print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... "
                          f"kcal={nutrition.get('kcal','?')} "
                          f"P={nutrition.get('protein','?')} "
                          f"F={nutrition.get('fat','?')} "
                          f"C={nutrition.get('carbs','?')}")
                else:
                    print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... ⚠ 詳細取得失敗")
            else:
                print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... 詳細URLなし")

            items.append({
                "name":    item["name"],
                "price":   item["price"],
                "kcal":    nutrition.get("kcal"),
                "protein": nutrition.get("protein"),
                "fat":     nutrition.get("fat"),
                "carbs":   nutrition.get("carbs"),
            })

        result[cat["id"]] = {"label": cat["label"], "items": items}
        if ci < len(categories) - 1:
            sleep()

    return result

# ══════════════════════════════════════════
# ローソン
# ══════════════════════════════════════════

def parse_lawson_nutrition(soup):
    """
    詳細ページの dt/dd ペアで栄養成分が取れる:
    {"熱量": "247kcal", "たんぱく質": "6.2g", ...}
    """
    result = {}
    dts = soup.select("dt, dd")
    last_key = None
    data = {}
    for el in dts:
        t = el.get_text(strip=True)
        if el.name == "dt":
            last_key = t
        elif el.name == "dd" and last_key:
            data[last_key] = t
    m_kcal    = re.search(r"[\d.]+", data.get("熱量", ""))
    m_protein = re.search(r"[\d.]+", data.get("たんぱく質", ""))
    m_fat     = re.search(r"[\d.]+", data.get("脂質", ""))
    m_carbs   = re.search(r"[\d.]+", data.get("炭水化物", ""))
    if m_kcal:
        result["kcal"]    = round(float(m_kcal.group()))
        result["protein"] = float(m_protein.group()) if m_protein else None
        result["fat"]     = float(m_fat.group())     if m_fat     else None
        result["carbs"]   = float(m_carbs.group())   if m_carbs   else None
    return result

def scrape_lawson(categories):
    print(f"\n{'='*50}\n🏪 ローソン\n{'='*50}")
    result = {}
    for ci, cat in enumerate(categories):
        print(f"\n[カテゴリ {ci+1}/{len(categories)}] {cat['label']}")
        soup = fetch(cat["url"])
        if not soup:
            result[cat["id"]] = {"label": cat["label"], "items": []}
            continue

        raw_items = []
        for li in soup.select(".productList section li"):
            name_el = li.select_one(".ttl")
            spans   = li.select(".price span")
            link_el = li.select_one("a[href*='/recommend/original/detail/']")
            if not name_el or not spans:
                continue
            m = re.match(r"^(\d+)$", spans[0].get_text(strip=True))
            if not m:
                continue
            raw_items.append({
                "name":       name_el.get_text(strip=True),
                "price":      int(m.group(1)),
                "detail_url": link_el["href"] if link_el else None,
            })

        print(f"  一覧取得: {len(raw_items)}件 → 詳細ページを巡回します")

        items = []
        for i, item in enumerate(raw_items):
            nutrition = {}
            if item["detail_url"]:
                sleep()
                detail_soup = fetch(item["detail_url"])
                if detail_soup:
                    nutrition = parse_lawson_nutrition(detail_soup)
                    print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... "
                          f"kcal={nutrition.get('kcal','?')} "
                          f"P={nutrition.get('protein','?')} "
                          f"F={nutrition.get('fat','?')} "
                          f"C={nutrition.get('carbs','?')}")
                else:
                    print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... ⚠ 詳細取得失敗")
            items.append({
                "name":    item["name"],
                "price":   item["price"],
                "kcal":    nutrition.get("kcal"),
                "protein": nutrition.get("protein"),
                "fat":     nutrition.get("fat"),
                "carbs":   nutrition.get("carbs"),
            })

        result[cat["id"]] = {"label": cat["label"], "items": items}
        if ci < len(categories) - 1:
            sleep()

    return result

# ══════════════════════════════════════════
# ファミマ
# ══════════════════════════════════════════

def parse_famima_nutrition(soup):
    """
    詳細ページのテーブル:
    tr[0]: 熱量（kcal） | たんぱく質（g） | 脂質（g） | 炭水化物（g） | 食塩相当量（g）
    tr[1]: 176.00 | 4.70 | 1.00 | 37.20 | 1.20
    """
    result = {}
    table = soup.select_one("table")
    if not table:
        return result
    rows = table.select("tr")
    if len(rows) < 2:
        return result
    headers = [th.get_text(strip=True) for th in rows[0].select("th, td")]
    values  = [td.get_text(strip=True) for td in rows[1].select("th, td")]
    data = dict(zip(headers, values))
    def get_val(key):
        for k, v in data.items():
            if key in k:
                m = re.search(r"[\d.]+", v)
                return float(m.group()) if m else None
        return None
    kcal = get_val("熱量")
    if kcal is not None:
        result["kcal"]    = round(kcal)
        result["protein"] = get_val("たんぱく質")
        result["fat"]     = get_val("脂質")
        result["carbs"]   = get_val("炭水化物")
    return result

def scrape_famima(categories):
    print(f"\n{'='*50}\n🏪 ファミリーマート\n{'='*50}")
    result = {}
    for ci, cat in enumerate(categories):
        print(f"\n[カテゴリ {ci+1}/{len(categories)}] {cat['label']}")
        soup = fetch(cat["url"])
        if not soup:
            result[cat["id"]] = {"label": cat["label"], "items": []}
            continue

        raw_items = []
        seen_urls = set()
        for card in soup.select("div.ly-mod-infoset3"):
            name_el  = card.select_one(".ly-mod-infoset3-name")
            price_el = card.select_one(".ly-mod-infoset3-price")
            link_el  = card.select_one(".ly-mod-infoset3-link")
            if not name_el or not price_el:
                continue
            name = re.sub(r"^【[^】]+】", "", name_el.get_text(strip=True)).strip()
            text = price_el.get_text(strip=True)
            m_tax  = re.search(r"税込(\d+)円", text)
            m_base = re.match(r"^(\d+)円", text)
            price = int(m_tax.group(1)) if m_tax else (int(m_base.group(1)) if m_base else None)
            if price is None:
                continue
            detail_url = link_el["href"] if link_el and link_el.get("href") else None
            if detail_url:
                if not detail_url.startswith("http"):
                    detail_url = "https://www.family.co.jp" + detail_url
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
            raw_items.append({"name": name, "price": price, "detail_url": detail_url})

        print(f"  一覧取得: {len(raw_items)}件 → 詳細ページを巡回します")

        items = []
        for i, item in enumerate(raw_items):
            nutrition = {}
            if item["detail_url"]:
                sleep()
                detail_soup = fetch(item["detail_url"])
                if detail_soup:
                    nutrition = parse_famima_nutrition(detail_soup)
                    print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... "
                          f"kcal={nutrition.get('kcal','?')} "
                          f"P={nutrition.get('protein','?')} "
                          f"F={nutrition.get('fat','?')} "
                          f"C={nutrition.get('carbs','?')}")
                else:
                    print(f"  [{i+1}/{len(raw_items)}] {item['name'][:20]}... ⚠ 詳細取得失敗")
            items.append({
                "name":    item["name"],
                "price":   item["price"],
                "kcal":    nutrition.get("kcal"),
                "protein": nutrition.get("protein"),
                "fat":     nutrition.get("fat"),
                "carbs":   nutrition.get("carbs"),
            })

        result[cat["id"]] = {"label": cat["label"], "items": items}
        if ci < len(categories) - 1:
            sleep()

    return result

# ══════════════════════════════════════════
# Gist保存
# ══════════════════════════════════════════

def save_to_gist(data):
    print("\n📤 Gistにアップロード中...")
    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={
            "Authorization": f"token {GIST_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={"files": {GIST_FILE: {"content": json.dumps(data, ensure_ascii=False)}}},
        timeout=15,
    )
    r.raise_for_status()
    print("✅ Gist保存完了！")

# ══════════════════════════════════════════
# メイン
# ══════════════════════════════════════════

def main():
    if not GIST_TOKEN:
        print("❌ GIST_TOKEN が設定されていません")
        print("   Windows: set GIST_TOKEN=ghp_xxxxxxxxxxxx")
        print("   Mac/Linux: export GIST_TOKEN=ghp_xxxxxxxxxxxx")
        return

    start = datetime.now()
    print(f"🚀 開始: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("⏱  所要時間の目安: 約2〜2.5時間")

    data = {"updated_at": start.isoformat(), "stores": {}}

    data["stores"]["seven"] = {
        "label": "セブン-イレブン",
        "categories": scrape_seven(SEVEN_CATEGORIES),
    }
    sleep()
    data["stores"]["lawson"] = {
        "label": "ローソン",
        "categories": scrape_lawson(LAWSON_CATEGORIES),
    }
    sleep()
    data["stores"]["famima"] = {
        "label": "ファミリーマート",
        "categories": scrape_famima(FAMIMA_CATEGORIES),
    }

    total = sum(
        len(c["items"])
        for s in data["stores"].values()
        for c in s["categories"].values()
    )
    elapsed = int((datetime.now() - start).total_seconds() / 60)
    print(f"\n✅ スクレイプ完了: {total}件 / {elapsed}分")

    save_to_gist(data)
    print(f"\n🎉 完了！ https://konbini-gacha.onrender.com を開いてください")


if __name__ == "__main__":
    main()
