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
- **Simulador de Portafolio y Paper Trading Profesional** — Motor contable de libro mayor (event-sourcing ledger) para auditar y simular inversiones con capital inicial ($100.000 USD por defecto, simulando brokers como Fintual, Interactive Brokers o Schwab). Seguimiento estricto de transacciones, coste medio ponderado (WAC), P&L realizado vs no realizado, comisiones y dividendos.
- **Analisis y Concentracion de Cartera** — Evaluacion automatica de asignacion de capital (% acciones, % REITs, % ETFs, % efectivo), exposicion sectorial y calculo del Indice Herfindahl-Hirschman (HHI) para medir concentracion del riesgo.
- **Dashboards Visuales de Portafolio (Plotly + Rich)** — Monitor integral en terminal con tablas formateadas y generacion de dashboards interactivos HTML con donas de asset allocation, distribucion sectorial y barras de rendimiento por activo.
- **Suite de Pruebas Automatizadas (Pytest)** — 29 tests unitarios que garantizan la integridad de la logica contable del portafolio, clasificadores de activos, analisis de estados financieros y extraccion de la SEC.
- **Intrinsic Value Calculator** (Planned) — DCF, Graham Formula, y multiplos comparables.
- **Margin of Safety** (Planned) — Comparacion visual de precio de mercado vs. valor intrinseco.

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **Data Sources**: yfinance, SEC EDGAR API (public 10-K & 10-Q filings)
- **Analysis**: pandas, numpy
- **Visualization**: rich (terminal), plotly (interactive dark mode web charts)
- **Testing**: pytest
- **Architecture**: OOP con principios SOLID, Factory Pattern, Event Sourcing Ledger

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
│   ├── portfolio/                    # Motor contable y simulador de portafolio
│   │   ├── portfolio_manager.py      # Event-sourcing ledger (compras, ventas, WAC, P&L)
│   │   └── portfolio_analytics.py    # Asignacion de activos, sectores e indice HHI
│   ├── valuation/                    # (Planned) Modelos de valoracion
│   ├── visualization/
│   │   ├── financial_charts.py       # Renderizado en terminal y graficos Plotly (SEC)
│   │   └── portfolio_charts.py       # Dashboards de portafolio en terminal y HTML Plotly
│   ├── main_data_update.py           # Orquestador: descarga de datos de mercado
│   ├── main_financial_history.py     # Orquestador: historico 10-K/10-Q y graficos
│   ├── main_analysis.py              # Orquestador: visualizacion de metricas y CLI
│   └── main_portfolio.py             # Orquestador: simulador de portafolio y paper trading
├── config/
│   ├── watchlist.json                # Lista manual de activos bajo seguimiento
│   └── moat_ratings.json             # Evaluaciones y tesis cualitativas de Moat
├── data/
│   ├── cache/                        # Cache local de fundamentales, precios y SEC
│   └── portfolio/                    # Ledger inmutable de transacciones y configuracion
├── exports/
│   └── charts/                       # Graficos interactivos HTML generados con Plotly
├── tests/                            # 29 tests unitarios automatizados con pytest
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

### 4. Simulador de Portafolio y Paper Trading ($100.000 USD)
Motor de libro mayor contable (event-sourcing ledger) para auditar y simular inversiones en condiciones reales de mercado (simulando brokers como Fintual, Interactive Brokers o Charles Schwab):
```powershell
# Ver resumen del portafolio (NAV total, caja disponible, posiciones abiertas, coste base WAC y P&L no realizado)
python src/main_portfolio.py

# Abrir dashboard visual interactivo en el navegador con graficos Plotly (asignacion, sectores y P&L)
python src/main_portfolio.py --plot

# Simular compra de acciones (ej: 50 acciones de DaVita a $148.50)
python src/main_portfolio.py --buy --ticker DVA --shares 50 --price 148.50 --fee 1.50 --notes "Tesis Moat Duopolio"

# Simular venta con calculo automatico de P&L realizado (ej: vender 20 acciones de DVA a $165.00)
python src/main_portfolio.py --sell --ticker DVA --shares 20 --price 165.00 --fee 1.50 --notes "Toma parcial de beneficios"

# Registrar cobro de dividendos o depositos/retiros de capital
python src/main_portfolio.py --dividend --ticker AAPL --price 45.00 --notes "Dividendo Q3"
python src/main_portfolio.py --deposit --price 10000.00 --notes "Aporte mensual"

# Ver historial completo de transacciones auditadas
python src/main_portfolio.py --history

# Reiniciar simulador a los $100.000 USD iniciales
python src/main_portfolio.py --reset
```

### 5. Configurar la watchlist y tesis de Moat
- **Watchlist (`config/watchlist.json`):** Edita manualmente para agregar o quitar activos (`ticker`, `name`, `sector`, `type`).
- **Tesis de Moat (`config/moat_ratings.json`):** Documenta para cada empresa su calificacion (`Wide`, `Narrow`, `None`), tendencia, fuentes activas de foso (costes de cambio, regulatorios, efectos de red, etc.), tesis cualitativa y riesgos de disrupcion.

Tipos soportados en la watchlist:
| Tipo | Descripcion | Ejemplo |
|---|---|---|
| `equity` | Acciones individuales | AAPL, MSFT, DVA, KO |
| `reit` | REITs (evaluados con FFO/AFFO) | O |
| `equity_etf` | ETFs de renta variable | JEPI, SCHD, VNQ |
| `bond_etf` | ETFs de renta fija | TLT, IEF, SHY |

### 6. Ejecutar pruebas unitarias (Pytest)
El proyecto cuenta con 29 tests unitarios automatizados que cubren el ledger contable, el analizador de estados financieros, los extractores SEC y los gestores de moat:
```powershell
pytest -v
```

## 📝 License

MIT License

