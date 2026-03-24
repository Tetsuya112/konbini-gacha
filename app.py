"""コンビニガチャ - Web API サーバー"""
from flask import Flask, jsonify, send_from_directory
import json, os

app = Flask(__name__, static_folder="static", static_url_path="")

_data_dir = "/data" if os.path.isdir("/data") else os.path.join(os.path.dirname(__file__), "data")
DATA_PATH = os.path.join(_data_dir, "products.json")

def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)

@app.route("/api/products")
def products():
    data = load_data()
    if not data:
        return jsonify({"error": "データがありません。scraper/scrape.py を先に実行してください。"}), 404
    return jsonify(data)

@app.route("/api/status")
def status():
    data = load_data()
    if not data:
        return jsonify({"updated_at": None, "total": 0})
    total = sum(len(cat["items"]) for store in data["stores"].values() for cat in store["categories"].values())
    return jsonify({"updated_at": data.get("updated_at"), "total": total})

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
