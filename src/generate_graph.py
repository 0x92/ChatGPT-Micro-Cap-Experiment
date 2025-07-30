from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf


BASE_DIR = Path(__file__).resolve().parents[1]


def generate_graph(save_path: str | None = None, show: bool = True) -> None:
    """Generate the performance graph and optionally save it."""

    # === Load and prepare ChatGPT portfolio ===
    portfolio_file = BASE_DIR / "Scripts and CSV Files" / "chatgpt_portfolio_update.csv"
    chatgpt_df = pd.read_csv(portfolio_file)
    chatgpt_totals = chatgpt_df[chatgpt_df['Ticker'] == 'TOTAL'].copy()
    chatgpt_totals['Date'] = pd.to_datetime(chatgpt_totals['Date'])

    # Add fake baseline row for June 27 (weekend)
    baseline_date = pd.Timestamp("2025-06-27")
    baseline_equity = 100  # Starting value
    baseline_chatgpt_row = pd.DataFrame({
        "Date": [baseline_date],
        "Total Equity": [baseline_equity]
    })
    chatgpt_totals = pd.concat([baseline_chatgpt_row, chatgpt_totals], ignore_index=True).sort_values("Date")

    # === Download and prepare Russell 2000 ===
    start_date = baseline_date
    end_date = chatgpt_totals['Date'].max()

    russell = yf.download("^RUT", start=start_date, end=end_date + pd.Timedelta(days=1), progress=False)
    russell = russell.reset_index()

    xbi = yf.download("XBI", start=start_date, end=end_date + pd.Timedelta(days=1), progress=False)
    xbi = xbi.reset_index()

    # Fix columns if downloaded with MultiIndex
    if isinstance(russell.columns, pd.MultiIndex):
        russell.columns = russell.columns.get_level_values(0)

    # Now clean and rename
    russell["Date"] = pd.to_datetime(russell["Date"])
    # Real close prices on June 27 (pulled from YF)
    xbi_27_price = 83.68000030517578
    russell_27_price = 2172.110107421875

    # Normalize to $100 baseline
    russell_scaling_factor = 100 / russell_27_price
    xbi_scaling_factor = 100 / xbi_27_price
    # create adjusted close col
    xbi["XBI Value ($100 Invested)"] = xbi["Close"] * xbi_scaling_factor
    russell["Russell Value ($100 Invested)"] = russell["Close"] * russell_scaling_factor

    # === Plot ===
    plt.figure(figsize=(10, 6))
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.plot(chatgpt_totals['Date'], chatgpt_totals["Total Equity"], label="ChatGPT ($100 Invested)", marker="o", color="blue", linewidth=2)
    plt.plot(russell['Date'], russell["Russell Value ($100 Invested)"], label="Russell 2000 ($100 Invested)", marker="o", color="orange", linestyle='--', linewidth=2)
    plt.plot(xbi['Date'], xbi["XBI Value ($100 Invested)"], label="XBI ($100 Invested)", marker="o", color="green", linestyle='--', linewidth=2)

    final_date = chatgpt_totals['Date'].iloc[-1]
    final_chatgpt = chatgpt_totals["Total Equity"].iloc[-1]
    final_russell = russell["Russell Value ($100 Invested)"].iloc[-1]
    final_xbi = xbi["XBI Value ($100 Invested)"].iloc[-1]

    plt.text(final_date, final_chatgpt + 0.3, f"+{final_chatgpt - 100:.1f}%", color="blue", fontsize=9)
    plt.text(final_date, final_russell + 0.3, f"+{final_russell - 100:.1f}%", color="orange", fontsize=9)
    plt.text(final_date, final_xbi + 0.6, f"+{final_xbi - 100:.1f}%", color="green", fontsize=9)

    drawdown_date = pd.Timestamp("2025-07-11")
    drawdown_value = 102.46
    plt.text(drawdown_date, drawdown_value - 1, "-7% Drawdown", color="red", fontsize=9)
    plt.title("ChatGPT vs. Russell 2000 vs. XBI")
    plt.xlabel("Date")
    plt.ylabel("Value of $100 Investment")
    plt.xticks(rotation=15)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
    if show:
        plt.show()


if __name__ == "__main__":
    generate_graph()
