# 📊 Fundamental Analysis Hub

Plataforma de analisis fundamental para value investing, con descarga automatizada de datos financieros, clasificacion inteligente de activos y metricas clave por tipo de instrumento.

## 🎯 Features

- **Watchlist Manual** — Lista de activos configurada manualmente en `config/watchlist.json` (en el futuro se integrara un screener automatizado como Finviz).
- **Clasificacion de Activos (OOP/SOLID)** — Cada activo se clasifica por tipo (`equity`, `reit`, `equity_etf`, `bond_etf`) y se analiza con las metricas que le corresponden.
- **Descarga y Cache de Datos** — Datos financieros descargados de Yahoo Finance y almacenados localmente en `data/cache/` con validez temporal de 24 horas.
- **Analisis de Metricas Clave** — Dashboard en terminal que muestra P/E, ROE, Margenes, Dividend Yield, Payout Ratio, FFO (REITs), Expense Ratio (ETFs), y mas.
- **Intrinsic Value Calculator** (Planned) — DCF, Graham Formula, y multiplos comparables.
- **Margin of Safety** (Planned) — Comparacion visual de precio de mercado vs. valor intrinseco.

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **Data Sources**: yfinance
- **Analysis**: pandas, numpy
- **Visualization**: rich (terminal), plotly (planned)
- **Architecture**: OOP con principios SOLID, Factory Pattern

## 📁 Project Structure

```
fundamental-analysis-hub/
├── src/
│   ├── data/
│   │   ├── watchlist_manager.py   # CRUD de la watchlist
│   │   └── downloader.py         # Descarga y cache de datos financieros
│   ├── analysis/
│   │   ├── base_analyzer.py      # Clase abstracta base (AssetAnalyzer)
│   │   ├── equity_analyzer.py    # Analizador para acciones
│   │   ├── reit_analyzer.py      # Analizador para REITs (FFO/AFFO)
│   │   ├── etf_analyzer.py       # Analizadores para ETFs (equity + bonds)
│   │   └── analyzer_factory.py   # Factory Pattern
│   ├── valuation/                # (Planned) Modelos de valoracion
│   ├── portfolio/                # (Planned) Seguimiento de portafolio
│   ├── visualization/            # (Planned) Graficos y dashboards
│   ├── main_data_update.py       # Orquestador: descarga de datos
│   └── main_analysis.py          # Orquestador: visualizacion de metricas
├── config/
│   └── watchlist.json            # Lista manual de activos bajo seguimiento
├── data/
│   └── cache/                    # Datos financieros descargados (ignorado por Git)
├── tests/
├── notebooks/
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

## 📊 Uso

### 1. Actualizar datos financieros
Descarga los estados financieros y precios historicos de todos los activos en la watchlist.
```powershell
python src/main_data_update.py           # Usa cache si tiene menos de 24h
python src/main_data_update.py --force   # Fuerza re-descarga desde Yahoo Finance
```

### 2. Ver metricas fundamentales
Muestra tablas de metricas clave agrupadas por tipo de activo (Equities, REITs, ETFs).
```powershell
python src/main_analysis.py
```

### 3. Configurar la watchlist
Edita manualmente el archivo `config/watchlist.json` para agregar o quitar activos.
Cada entrada requiere: `ticker`, `name`, `sector` y `type`.

Tipos soportados:
| Tipo | Descripcion | Ejemplo |
|---|---|---|
| `equity` | Acciones individuales | AAPL, MSFT, PFE |
| `reit` | REITs (evaluados con FFO/AFFO) | O |
| `equity_etf` | ETFs de renta variable | JEPI, SCHD, VNQ |
| `bond_etf` | ETFs de renta fija | TLT, IEF, SHY |

## 📝 License

MIT License
