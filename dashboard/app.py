from flask import Flask, send_file, render_template_string
import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "Scripts and CSV Files"
GRAPH_DIR = BASE_DIR / "graphs"

sys.path.append(str(CSV_DIR))
from Generate_Graph import generate_graph

app = Flask(__name__)

@app.route("/")
def show_portfolio():
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    return render_template_string("""
    <h1>Portfolio</h1>
    {{table|safe}}
    """, table=df.to_html(index=False))

@app.route("/log")
def show_log():
    file_candidates = [BASE_DIR / "chatgpt_trade_log.csv", CSV_DIR / "chatgpt_trade_log.csv"]
    file_path = next((p for p in file_candidates if p.exists()), None)
    if not file_path:
        return "Trade log not found", 404
    df = pd.read_csv(file_path)
    return render_template_string("""
    <h1>Trade Log</h1>
    {{table|safe}}
    """, table=df.to_html(index=False))

@app.route("/graph")
def show_graph():
    GRAPH_DIR.mkdir(exist_ok=True)
    png_files = list(GRAPH_DIR.glob("*.png"))
    if png_files:
        latest = max(png_files, key=lambda p: p.stat().st_mtime)
    else:
        latest = GRAPH_DIR / "performance.png"
        generate_graph(latest.as_posix(), show=False)
    return send_file(latest, mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)
