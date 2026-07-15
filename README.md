# 📊 Fundamental Analysis Hub

A Python-based value investing portfolio tracker and intrinsic value analyzer.

## 🎯 Features (Planned)

- **Intrinsic Value Calculator** — Automated DCF, Graham Formula, and comparable multiples analysis
- **Financial Statement Analysis** — Revenue, earnings, margins, and growth trends
- **Key Ratios Dashboard** — P/E, P/B, EV/EBITDA, ROE, ROIC, Debt/Equity, and more
- **Margin of Safety** — Visual comparison of market price vs. intrinsic value
- **Portfolio Tracker** — Track your value investing positions and performance
- **Watchlist (Manual)** — Monitor a hand-picked watchlist configured manually in `config/watchlist.json` (plans to add an automated screener like Finviz in the future).
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

```powershell
# 1. Clonar el repositorio
git clone https://github.com/ronaldreighsrsc/fundamental-analysis-hub.git

# 2. Crear el entorno virtual (usando py en Windows)
py -m venv venv

# 3. Activar el entorno virtual en Windows:
# En PowerShell (Editor por defecto en VS Code):
.\venv\Scripts\Activate.ps1
# O en CMD:
venv\Scripts\activate
# O en Git Bash / Linux / Mac:
source venv/Scripts/activate

# 4. Instalar las dependencias
pip install -r requirements.txt

# 5. Probar que todo funciona correctamente
python verify_setup.py

# 6. Configurar variables de entorno
copy .env.example .env
# Luego edita el archivo .env con tus credenciales
```

## 📝 License

MIT License
