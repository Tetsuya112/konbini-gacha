"""コンビニガチャ - Web API サーバー（スクレイパー内蔵版）"""
from flask import Flask, jsonify, send_from_directory, request
import json, os, threading

app = Flask(__name__, static_folder="static", static_url_path="")

DATA_PATH = "/tmp/products.json"
SCRAPE_TOKEN = os.environ.get("SCRAPE_TOKEN", "dev-token")

def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)

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
    token = request.args.get("token", "")
    if token != SCRAPE_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    # バックグラウンドで実行
    def run():
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        from scraper.scrape import main
        main()
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

def startup_scrape():
    """起動時にデータがなければ自動スクレイプ"""
    if not os.path.exists(DATA_PATH):
        print("🚀 初回起動: スクレイピングを開始します...")
        from scraper.scrape import main
        t = threading.Thread(target=main, daemon=True)
        t.start()

if __name__ == "__main__":
    startup_scrape()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
