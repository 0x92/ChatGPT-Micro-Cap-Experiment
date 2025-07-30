from flask import Flask, send_file, render_template_string, url_for
import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "Scripts and CSV Files"
GRAPH_DIR = BASE_DIR / "graphs"

sys.path.append(str(CSV_DIR))
from Generate_Graph import generate_graph

app = Flask(__name__)


def render_page(content: str) -> str:
    """Wrap content in a basic page with navigation links."""
    nav = (
        f'<nav>'
        f'<a href="{url_for("show_portfolio")}">Portfolio</a> | '
        f'<a href="{url_for("show_log")}">Trade Log</a> | '
        f'<a href="{url_for("show_graph")}">Graph</a> | '
        f'<a href="{url_for("show_summary")}">Summary</a>'
        f'</nav><hr>'
    )
    return render_template_string("""{{nav|safe}}{{content|safe}}""", nav=nav, content=content)

@app.route("/")
def show_portfolio():
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    content = f"<h1>Portfolio</h1>{df.to_html(index=False)}"
    return render_page(content)

@app.route("/log")
def show_log():
    file_candidates = [BASE_DIR / "chatgpt_trade_log.csv", CSV_DIR / "chatgpt_trade_log.csv"]
    file_path = next((p for p in file_candidates if p.exists()), None)
    if not file_path:
        return "Trade log not found", 404
    df = pd.read_csv(file_path)
    content = f"<h1>Trade Log</h1>{df.to_html(index=False)}"
    return render_page(content)

@app.route("/graph_image")
def graph_image():
    GRAPH_DIR.mkdir(exist_ok=True)
    png_files = list(GRAPH_DIR.glob("*.png"))
    if png_files:
        latest = max(png_files, key=lambda p: p.stat().st_mtime)
    else:
        latest = GRAPH_DIR / "performance.png"
        generate_graph(latest.as_posix(), show=False)
    return send_file(latest, mimetype="image/png")


@app.route("/graph")
def show_graph():
    img_tag = f'<img src="{url_for("graph_image")}" alt="Performance graph">'
    return render_page(img_tag)


@app.route("/summary")
def show_summary():
    file_path = CSV_DIR / "chatgpt_portfolio_update.csv"
    if not file_path.exists():
        return "Portfolio file not found", 404
    df = pd.read_csv(file_path)
    totals = df[df["Ticker"] == "TOTAL"]
    if totals.empty:
        return "No summary data", 404
    latest = totals.iloc[-1]
    summary = f"""
    <h1>Summary ({latest['Date']})</h1>
    <ul>
        <li>Total Value: {latest['Total Value']}</li>
        <li>PnL: {latest['PnL']}</li>
        <li>Cash Balance: {latest['Cash Balance']}</li>
        <li>Total Equity: {latest['Total Equity']}</li>
    </ul>
    """
    return render_page(summary)

if __name__ == "__main__":
    app.run(debug=True)
