# 📊 Fundamental Analysis Hub

A Python-based value investing portfolio tracker and intrinsic value analyzer.

## 🎯 Features (Planned)

- **Intrinsic Value Calculator** — Automated DCF, Graham Formula, and comparable multiples analysis
- **Financial Statement Analysis** — Revenue, earnings, margins, and growth trends
- **Key Ratios Dashboard** — P/E, P/B, EV/EBITDA, ROE, ROIC, Debt/Equity, and more
- **Margin of Safety** — Visual comparison of market price vs. intrinsic value
- **Portfolio Tracker** — Track your value investing positions and performance
- **Watchlist** — Monitor undervalued stocks with automated alerts
- **Step-by-Step Analysis** — Guided valuation process with explanations

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Data Sources**: yfinance, Financial Modeling Prep API, SEC EDGAR
- **Analysis**: pandas, numpy
- **Visualization**: plotly, matplotlib
- **Interface**: TBD (Streamlit / CLI / Web)

## 📁 Project Structure

```
fundamental-analysis-hub/
├── src/
│   ├── data/              # Data fetching and caching
│   ├── valuation/         # Valuation models (DCF, Graham, multiples)
│   ├── analysis/          # Financial statement analysis
│   ├── portfolio/         # Portfolio tracking and management
│   └── visualization/     # Charts and dashboards
├── tests/                 # Unit and integration tests
├── notebooks/             # Jupyter notebooks for exploration
├── config/                # Configuration files
├── data/                  # Cached financial data
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/fundamental-analysis-hub.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## 📝 License

MIT License
