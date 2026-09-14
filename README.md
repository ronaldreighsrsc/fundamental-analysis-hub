# 📊 Fundamental Analysis Hub

Plataforma de analisis fundamental para value investing, con descarga automatizada de datos financieros, clasificacion inteligente de activos y metricas clave por tipo de instrumento.

## 🎯 Features

- **Watchlist Manual** — Lista de activos configurada manualmente en `config/watchlist.json` (en el futuro se integrara un screener automatizado como Finviz).
- **Clasificacion de Activos (OOP/SOLID)** — Cada activo se clasifica por tipo (`equity`, `reit`, `equity_etf`, `bond_etf`) y se analiza con las metricas que le corresponden.
- **Descarga y Cache de Datos** — Datos financieros descargados de Yahoo Finance y almacenados localmente en `data/cache/` con validez temporal de 24 horas.
- **Analisis de Metricas Clave** — Dashboard en terminal que muestra P/E, ROE, Margenes, Dividend Yield, Payout Ratio, FFO (REITs), Expense Ratio (ETFs), y mas.
- **Analisis Cualitativo de Moat (Foso Economico)** — Evaluacion de ventajas competitivas duraderas basada en las 5 fuentes clasicas (Costes de cambio, Activos intangibles/Regulatorios, Efectos de red, Ventajas de costes y Escala eficiente), con tesis del inversor y amenazas de disrupcion.
- **Perspectiva de Inversores (Skin in the Game & Smart Money)** — Monitoreo de alineacion accionaria (% de directivos e insiders) y participacion de fondos institucionales, manteniendo un calculo independiente del valor intrinseco (sin sesgo de analistas ni cortos).
- **Historico Financiero Multianual (10-K y 10-Q SEC)** — Extraccion oficial y 100% gratuita de 10 a 17+ anios de estados financieros auditados directamente desde la SEC EDGAR API publica (ventas, beneficio neto, FCF, margenes historicos y recompras de acciones), sin pagar suscripciones a plataformas privadas.
- **Dashboards Graficos Interactivos (Plotly)** — Generacion automatica de graficos en HTML en modo oscuro profesional con subplots de ingresos vs beneficios, calidad de caja (FCF vs Net Income), evolucion del foso a traves de margenes y dilucion de acciones.
- **Intrinsic Value Calculator** (Planned) — DCF, Graham Formula, y multiplos comparables.
- **Margin of Safety** (Planned) — Comparacion visual de precio de mercado vs. valor intrinseco.

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **Data Sources**: yfinance, SEC EDGAR API (public 10-K & 10-Q filings)
- **Analysis**: pandas, numpy
- **Visualization**: rich (terminal), plotly (interactive dark mode web charts)
- **Architecture**: OOP con principios SOLID, Factory Pattern

## 📁 Project Structure

```
fundamental-analysis-hub/
├── src/
│   ├── data/
│   │   ├── watchlist_manager.py       # CRUD de la watchlist
│   │   ├── downloader.py             # Descarga y cache de Yahoo Finance
│   │   ├── sec_edgar_downloader.py   # Cliente para la API publica de la SEC EDGAR
│   │   └── sec_financial_extractor.py# Extractor de series contables 10-K y 10-Q
│   ├── analysis/
│   │   ├── base_analyzer.py          # Clase abstracta base (AssetAnalyzer)
│   │   ├── equity_analyzer.py        # Analizador para acciones (rentabilidad, deuda, ownership)
│   │   ├── moat_manager.py           # Gestor cualitativo de Moat y Tesis de Inversion
│   │   ├── reit_analyzer.py          # Analizador para REITs (FFO/AFFO)
│   │   ├── etf_analyzer.py           # Analizadores para ETFs (equity + bonds)
│   │   └── analyzer_factory.py       # Factory Pattern
│   ├── valuation/                    # (Planned) Modelos de valoracion
│   ├── portfolio/                    # (Planned) Seguimiento de portafolio
│   ├── visualization/
│   │   └── financial_charts.py       # Renderizado en terminal y graficos Plotly
│   ├── main_data_update.py           # Orquestador: descarga de datos de mercado
│   ├── main_financial_history.py     # Orquestador: historico 10-K/10-Q y graficos
│   └── main_analysis.py              # Orquestador: visualizacion de metricas y CLI
├── config/
│   ├── watchlist.json                # Lista manual de activos bajo seguimiento
│   └── moat_ratings.json             # Evaluaciones y tesis cualitativas de Moat
├── exports/
│   └── charts/                       # Graficos interactivos HTML generados con Plotly
├── data/
│   └── cache/                        # Cache local de fundamentales, precios y SEC
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

### 2. Ver metricas fundamentales y Moat
Muestra tablas de metricas clave agrupadas por tipo de activo, estructura de inversores y evaluacion cualitativa de ventajas competitivas.
```powershell
python src/main_analysis.py              # Resumen general de la watchlist
python src/main_analysis.py --ticker DVA # Analisis individual con ficha completa de Moat
python src/main_analysis.py --moat       # Resumen general + reporte cualitativo de Moat
python src/main_analysis.py --ticker DVA --history  # Con tabla historica multianual (10-K)
python src/main_analysis.py --ticker DVA --plot     # Abre dashboard interactivo Plotly
```

### 3. Historico Financiero Multianual y Graficos Interactivos (10-K / 10-Q SEC)
Extrae hasta 15+ anios de estados financieros auditados directamente desde la base publica de la SEC (EDGAR), sin pagar suscripciones a plataformas privadas.
```powershell
# Tabla evolutiva en terminal (Ventas, Margenes, FCF, Crecimiento YoY y barra visual)
python src/main_financial_history.py --ticker DVA

# Abrir dashboard interactivo en modo oscuro con Plotly en el navegador
python src/main_financial_history.py --ticker DVA --plot

# Ver ultimos 10 anios de una empresa
python src/main_financial_history.py --ticker AAPL --years 10 --plot

# Ver evolucion trimestral (10-Q)
python src/main_financial_history.py --ticker MSFT --period quarterly
```

### 4. Configurar la watchlist y tesis de Moat
- **Watchlist (`config/watchlist.json`):** Edita manualmente para agregar o quitar activos (`ticker`, `name`, `sector`, `type`).
- **Tesis de Moat (`config/moat_ratings.json`):** Documenta para cada empresa su calificacion (`Wide`, `Narrow`, `None`), tendencia, fuentes activas de foso (costes de cambio, regulatorios, efectos de red, etc.), tesis cualitativa y riesgos de disrupcion.

Tipos soportados en la watchlist:
| Tipo | Descripcion | Ejemplo |
|---|---|---|
| `equity` | Acciones individuales | AAPL, MSFT, DVA, KO |
| `reit` | REITs (evaluados con FFO/AFFO) | O |
| `equity_etf` | ETFs de renta variable | JEPI, SCHD, VNQ |
| `bond_etf` | ETFs de renta fija | TLT, IEF, SHY |

## 📝 License

MIT License
