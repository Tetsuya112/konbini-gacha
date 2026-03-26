"""
コンビニガチャ - Web API サーバー
/ → v1（価格のみ）
/v2 → v2（PFC対応）
"""
from flask import Flask, jsonify, send_from_directory, request
import json, os, threading, urllib.request

app = Flask(__name__)

SCRAPE_TOKEN = os.environ.get("SCRAPE_TOKEN", "dev-token")
GIST_TOKEN   = os.environ.get("GIST_TOKEN", "")

# v1
GIST_ID_V1  = os.environ.get("GIST_ID_V1", "e3064a46d4f39092cee0138cbe8a7e6c")
GIST_FILE_V1 = "konbini_products.json"

# v2
GIST_ID_V2  = os.environ.get("GIST_ID_V2", "")
GIST_FILE_V2 = "konbini_products_v2.json"

def load_gist(gist_id, filename):
    if not gist_id:
        return None
    try:
        url = f"https://gist.githubusercontent.com/raw/{gist_id}/{filename}"
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Gist load error ({gist_id}): {e}")
        return None

# ── v1 ─────────────────────────────────────

@app.route("/")
def index_v1():
    return send_from_directory("static", "index.html")

@app.route("/api/products")
def products_v1():
    data = load_gist(GIST_ID_V1, GIST_FILE_V1)
    if not data:
        return jsonify({"error": "データがありません"}), 404
    return jsonify(data)

@app.route("/api/status")
def status_v1():
    data = load_gist(GIST_ID_V1, GIST_FILE_V1)
    if not data:
        return jsonify({"updated_at": None, "total": 0})
    total = sum(len(c["items"]) for s in data["stores"].values() for c in s["categories"].values())
    return jsonify({"updated_at": data.get("updated_at"), "total": total, "version": "v1"})

# ── v2 ─────────────────────────────────────

@app.route("/v2")
@app.route("/v2/")
def index_v2():
    return send_from_directory("v2/static", "index.html")

@app.route("/v2/api/products")
def products_v2():
    data = load_gist(GIST_ID_V2, GIST_FILE_V2)
    if not data:
        return jsonify({"error": "データがありません（v2はまだスクレイプ未実行かも）"}), 404
    return jsonify(data)

@app.route("/v2/api/status")
def status_v2():
    data = load_gist(GIST_ID_V2, GIST_FILE_V2)
    if not data:
        return jsonify({"updated_at": None, "total": 0})
    total = sum(len(c["items"]) for s in data["stores"].values() for c in s["categories"].values())
    return jsonify({"updated_at": data.get("updated_at"), "total": total, "version": "v2"})

# ── 共通 ────────────────────────────────────

@app.route("/api/scrape")
def scrape_v1():
    if request.args.get("token") != SCRAPE_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    def run():
        import sys
        sys.path.insert(0, "v1")
        from scrape_and_upload import main
        main()
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started", "version": "v1"})

@app.route("/v2/api/scrape")
def scrape_v2():
    if request.args.get("token") != SCRAPE_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    def run():
        import sys
        sys.path.insert(0, "v2")
        from scrape_and_upload import main
        main()
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started", "version": "v2"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
