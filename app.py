"""コンビニガチャ - Web API（GitHub Gist永続化版）"""
from flask import Flask, jsonify, send_from_directory, request
import json, os, threading, urllib.request

app = Flask(__name__, static_folder="static", static_url_path="")

SCRAPE_TOKEN = os.environ.get("SCRAPE_TOKEN", "dev-token")
GIST_TOKEN   = os.environ.get("GIST_TOKEN", "")
GIST_ID      = os.environ.get("GIST_ID", "")
GIST_FILE    = "konbini_products.json"

def load_data():
    """Gistからデータを取得。なければNone"""
    if not GIST_ID:
        return None
    try:
        url = f"https://gist.githubusercontent.com/raw/{GIST_ID}/{GIST_FILE}"
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"Gist load error: {e}")
        return None

@app.route("/api/products")
def products():
    data = load_data()
    if not data:
        return jsonify({"error": "データ取得中です。数分後に再読み込みしてください。"}), 404
    return jsonify(data)

@app.route("/api/status")
def status():
    data = load_data()
    if not data:
        return jsonify({"updated_at": None, "total": 0})
    total = sum(len(c["items"]) for s in data["stores"].values() for c in s["categories"].values())
    return jsonify({"updated_at": data.get("updated_at"), "total": total})

@app.route("/api/scrape")
def scrape():
    if request.args.get("token") != SCRAPE_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    def run():
        from scraper.scrape import main
        main()
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
