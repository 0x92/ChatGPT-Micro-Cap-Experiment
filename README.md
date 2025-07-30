# ChatGPT Micro-Cap Experiment
Welcome to the repo behind my 6-month live trading experiment where ChatGPT manages a real-money micro-cap portfolio.

# The Concept
Everyday, I kept seeing the same ad about having an some A.I. pick undervalued stocks. It was obvious it was trying to get me to subscribe to some garbage, so I just rolled my eyes. 
Then I started wondering, "How well would that actually work?".

So, starting with just $100, I wanted to answer a simple but powerful question:

#### **Can powerful large language models like ChatGPT actually generate alpha (or at least make smart trading decisions) using real-time data?**

## Each trading day:

- I provide it trading data on the stocks in it's portfolio.

- Strict stop-loss rules apply.

- Everyweek I allow it to use deep research to reevaluate it's account.

- I track and publish performance data weekly on my blog. (https://substack.com/@nathanbsmith?utm_source=edit-profile-page)

  ## Research & Documentation

- [Research Index](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/blob/main/Deep%20Research%20Index.md) 
- [Markdown Research Summaries (MD)](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/tree/main/Weekly%20Deep%20Research%20(MD))
- [Weekly Deep Research Reports (PDF)](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment/tree/main/Weekly%20Deep%20Research%20(PDF))
  
# Performance Example (6/30 – 7/25)

---

![Week 4 Performance](%286-30%20-%207-25%29%20Results.png)

---
- Currently stomping on the Russell 2K.

# Features of This Repo
Live trading scripts — Used to evaluate prices and update holdings daily

LLM-powered decision engine — ChatGPT picks the trades

Performance tracking — CSVs with daily PnL, total equity, and trade history

Visualization tools — Matplotlib graphs comparing ChatGPT vs Index

Logs & trade data — Auto-saved logs for transparency

Price data caching — Avoids unnecessary yfinance requests by storing daily
quotes under `cache/`

# Why This Matters
AI is being hyped across every industry, but can it really manage money without guidance?

This project is an attempt to find out, with transparency, data, and a real budget.

# Tech Stack
Basic Python 

Pandas + yFinance for data & logic

Matplotlib for visualizations

ChatGPT 4o for decision-making

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Set up access to your brokerage API by exporting credentials before running the scripts:
```bash
export BROKER_API_KEY="<your-key>"
export BROKER_SECRET_KEY="<your-secret>"
# Optional: point to a different paper trading base URL
export BROKER_BASE_URL="https://paper-api.alpaca.markets"
```
This project uses the paper trading API only, so no real money is automatically traded.

The `src.broker` module now exposes helper functions to interact with the
Alpaca paper API. Use `place_order` to submit trades, `get_account` to fetch
account details and `list_positions` to inspect open positions.


# Follow Along
The experiment runs June 2025 to December 2025.
Every trading day I will update the portfolio CSV file.
If you feel inspired to do something simiar, feel free to use this as a blueprint.

Updates are posted weekly on my blog — more coming soon!

One final shameless plug: (https://substack.com/@nathanbsmith?utm_source=edit-profile-page)

Find a mistake in the logs or have advice?
Please Reach out here: nathanbsmith.business@gmail.com

## Example Usage

Run the trading script with your portfolio CSV and starting cash:

```bash
python "Scripts and CSV Files/Trading_Script.py" --portfolio my_portfolio.csv --cash 100
```

The trading script also saves a PNG graph under the `graphs/` directory each
time it runs. Open the generated file with any image viewer to see the latest
performance chart.
If a ticker's price history can't be retrieved (for example if yfinance has no
data), the program prints a warning and skips that symbol. Skipped tickers are
not written to the daily portfolio CSV and are ignored when calculating totals.


Cached price files are saved under `cache/` as pickles. The script checks this
folder each day and only queries yfinance when the file for that ticker and
date doesn't exist.

### Configuration File

You can store common settings in a `config.yaml` (or `.json`) file at the project
root. Parameters defined here are used as defaults when running the trading
script.

Example `config.yaml`:

```yaml
default_cash: 100.0
default_stop_loss: 0.05
extra_tickers:
  - "^RUT"
  - "IWO"
  - "XBI"
```

Run the script using the config (values provided on the command line override
the file):

```bash
python "Scripts and CSV Files/Trading_Script.py" --portfolio my_portfolio.csv --config config.yaml
```


## Dashboard

Start the Flask dashboard to view the portfolio, trade log, performance graph,
and a quick summary of the latest totals:

```bash
python dashboard/app.py
```

Visit `http://localhost:5000/` in your browser. Use the navigation links at the
top of the page to switch between the Portfolio, Trade Log, Graph, and Summary
views.

## Automating Daily Runs

Use `daily_run.py` to schedule `Trading_Script.py` every day.

```bash
python daily_run.py --portfolio my_portfolio.csv --cash 100 --time 09:00
```

### Background execution

Keep the scheduler running even after you close the terminal:

```bash
nohup python daily_run.py --portfolio my_portfolio.csv --cash 100 --time 09:00 &
```

### Cron example

Add this to your crontab to start at boot:

```
@reboot /usr/bin/python /path/to/daily_run.py --portfolio /path/to/my_portfolio.csv --cash 100 --time 09:00 >> /path/to/trade.log 2>&1
```
