# 📊 Fundamental Analysis Hub

Plataforma profesional de análisis fundamental para **Value Investing**, con extracción automatizada de datos contables auditados de la SEC (10-K y 10-Q), suite completa de **Modelos de Valuación de Valor Intrínseco**, clasificación inteligente de activos (OOP/SOLID), análisis cualitativo de Moat, motor contable de Portafolio y Terminal Web interactivo.

---

## 🎯 Features

- **Suite Completa de Modelos de Valuación de Valor Intrínseco (Fern Finance / Wall Street)**:
  - **Benjamin Graham Formula**: Fórmula clásica 1962 ($EPS \times (8.5 + 2g)$), fórmula revisada 1974 vinculada en tiempo real a los rendimientos de bonos corporativos AAA de la Reserva Federal (FRED API serie `AAA`), y variante conservadora ($7 + 1g$).
  - **WACC Calculator (Costo de Capital Ponderado)**: Costo de deuda antes y después de impuestos, Costo de Equity mediante CAPM ($R_f + \beta \times ERP$), y ponderaciones óptimas de estructura de capital ($W_d, W_e$).
  - **Multi-Stage DCF (Descuento de Flujos de Caja)**: Modelo a 5 años enlazado a los márgenes auditados de la SEC (Margen de Flujo Operativo, Margen de CapEx, FCF), valor terminal perpetuo Gordon Growth al 2.5% y cálculo de Margen de Seguridad.
  - **Forward P/E Projection Model**: Proyección a 5 años de ventas, margen de beneficio neto, **tasa de dilución o recompras de acciones (Buybacks)** libre de distorsiones por splits, Forward EPS, P/E terminal y tasa de retorno compuesto anual (CAGR).
  - **Dividend Discount Model (DDM)**: Modelo de Gordon Growth ($V = \frac{D_1}{r - g}$) enlazado al historial de dividendos de Yahoo Finance con validación de singularidad ($r > g$).
  - **Reverse DCF (Valuación Inversa)**: Solución numérica por bisección para descubrir la tasa de crecimiento de FCF que el precio actual descuenta en el mercado, comparada contra el crecimiento real histórico de la SEC.
- **Histórico Financiero Multianual (10-K y 10-Q SEC EDGAR)**:
  - Extracción oficial y 100% gratuita de hasta 17+ años de estados financieros auditados desde la SEC EDGAR API pública.
  - **Métricas de Solvencia y Salud Financiera (Módulos S08/S09)**:
    - **Current Ratio**: $\frac{\text{Current Assets}}{\text{Current Liabilities}}$ para evaluar liquidez a corto plazo.
    - **Prueba de Fuego de Solvencia / Net Cash**: Efectivo y equivalentes vs deuda total ($\text{Cash} - \text{Total Debt}$) para verificar inmunidad contra quiebra.
    - **Interest Coverage Ratio**: Cobertura operativa de intereses ($\frac{\text{Operating Income}}{\text{Interest Expense}}$) para detectar riesgos de estrés financiero.
  - **Basic vs Diluted EPS**: Seguimiento del beneficio por acción básico vs diluido con evolución histórica.
  - **Acciones en Circulación (Basic vs Diluted Shares)**: Detección precisa de dilución de accionistas vs recompras de acciones (Stock-Based Compensation tracking).
- **Análisis Cualitativo de Moat (Foso Económico)**:
  - Evaluación de ventajas competitivas duraderas basada en las 5 fuentes clásicas (Costes de cambio, Activos intangibles/Regulatorios, Efectos de red, Ventajas de costes y Escala eficiente).
  - Registro de tesis de inversión y monitoreo de riesgos de disrupción.
- **Perspectiva de Inversores (Skin in the Game & Smart Money)**:
  - Monitoreo de alineación accionaria (% directivos e insiders) y participación institucional.
- **Dashboards Gráficos Interactivos (Plotly)**:
  - Gráficos interactivos en HTML en modo oscuro profesional: Ingresos vs Beneficios, Calidad de Caja (FCF vs Net Income), Evolución de Márgenes y Dilución de Acciones.
- **Simulador de Portafolio y Paper Trading Profesional ($100.000 USD)**:
  - Motor contable de libro mayor (event-sourcing ledger) con seguimiento estricto de transacciones, coste medio ponderado (WAC), P&L realizado vs no realizado, comisiones y dividendos.
- **Generador de Reportes de Cobertura Institucional (Equity Research One-Pager)**:
  - Generación automatizada de reportes de iniciación de cobertura en formato Markdown (`reports/`) listos para comités de inversión.
  - Integra los 3 pilares: Resumen ejecutivo y recomendación formal (**BUY / HOLD / SELL**), calidad de negocio y Moat, escudo de solvencia y auditoría de dilución por SBC, y matriz comparativa de los 7 modelos de valuación con consenso de *Fair Value*.
  - Reportes de muestra pregenerados: `reports/AAPL_Equity_Research_Report.md`, `reports/KO_Equity_Research_Report.md`, y `reports/DVA_Equity_Research_Report.md`.
- **Web App: Terminal Dual (Trading Desk & Research Fundamental)**:
  - Conmutador de vista en tiempo real entre:
    1. **Trading Desk & Portafolio PME**: Seguimiento contable con alpha contra el S&P 500, HHI y gestión de órdenes.
    2. **Terminal de Equity Research & Valuación (3 Pilares)**: Búsqueda instantánea de cualquier ticker (`AAPL`, `KO`, `DVA`, etc.) con tarjetas visuales de Moat, solvencia, dilución y matriz interactiva de los 7 modelos de valuación.
- **Suite de Pruebas Automatizadas (Pytest)**:
  - **62 tests unitarios** que cubren el 100% de la lógica contable, analizadores de activos, extractores de la SEC, API web, generador de research y la suite completa de valuación.

---

## 🛠️ Tech Stack

- **Lenguaje**: Python 3.12+, HTML5, Vanilla CSS, Vanilla JavaScript (SPA)
- **Fuentes de Datos**: SEC EDGAR API (10-K y 10-Q públicos), Yahoo Finance API, FRED Federal Reserve Economic Data
- **Cálculo y Modelado**: pandas, numpy, scipy / bisect
- **Visualización**: Rich (tablas y dashboards para terminal), Plotly (gráficos web interactivos en modo oscuro)
- **Testing**: pytest (62 tests unitarios automatizados - 100% pass rate)
- **Arquitectura**: Principios SOLID, Factory Pattern, Event Sourcing Ledger, Arquitectura Modular y REST API

---

## 📁 Estructura del Proyecto

```
├── reports/                          # 📄 REPORTES INSTITUCIONALES DE EQUITY RESEARCH
│   ├── AAPL_Equity_Research_Report.md# Iniciación de cobertura Apple Inc. (SELL)
│   ├── KO_Equity_Research_Report.md  # Iniciación de cobertura The Coca-Cola Co. (HOLD)
│   └── DVA_Equity_Research_Report.md # Iniciación de cobertura DaVita Inc. (BUY)
├── src/
│   ├── data/
│   │   ├── watchlist_manager.py       # CRUD de la watchlist
│   │   ├── downloader.py             # Descarga y cache de Yahoo Finance
│   │   ├── sec_edgar_downloader.py   # Cliente para la API publica de la SEC EDGAR
│   │   └── sec_financial_extractor.py# Extractor de series 10-K/10-Q (EPS, Dilucion, FCF, Solvencia)
│   ├── analysis/
│   │   ├── base_analyzer.py          # Clase abstracta base (AssetAnalyzer)
│   │   ├── equity_analyzer.py        # Analizador de acciones (rentabilidad, deuda, ownership)
│   │   ├── moat_manager.py           # Gestor cualitativo de Moat y Tesis de Inversion
│   │   ├── research_report_generator.py # 🎯 Generador institucional de reportes (3 Pilares)
│   │   ├── reit_analyzer.py          # Analizador de REITs (FFO/AFFO)
│   │   ├── etf_analyzer.py           # Analizadores de ETFs (equity y renta fija)
│   │   └── analyzer_factory.py       # Factory Pattern
│   ├── valuation/                    # 🎯 SUITE DE VALUACION DE VALOR INTRINSECO
│   │   ├── graham_valuation.py       # Graham 1962, Revised 1974 (FRED AAA Yield) y Conservador
│   │   ├── wacc_calculator.py        # WACC, Cost of Debt (after-tax), CAPM Cost of Equity
│   │   ├── dcf_valuation.py          # Multi-Stage DCF a 5 anos con margenes SEC y Gordon Growth
│   │   ├── pe_forward_valuation.py   # Forward P/E a 5 anos con Buybacks / Dilucion y CAGR
│   │   ├── dividend_discount_model.py# Gordon Growth Dividend Discount Model (DDM)
│   │   ├── reverse_dcf.py            # Valuacion Inversa (Crecimiento Implicito vs SEC CAGR)
│   │   └── relative_multiples.py     # Multiplos Relativos (PEG Peter Lynch, P/E Mi Favorita, P/S, P/B, P/CF)
│   ├── portfolio/                    # Motor contable y simulador de portafolio
│   │   ├── portfolio_manager.py      # Event-sourcing ledger (compras, ventas, WAC, P&L)
│   │   └── portfolio_analytics.py    # Asignacion de activos, sectores e indice HHI
│   ├── web/                          # Aplicacion Web Interactiva (Broker & Research Terminal)
│   │   ├── server.py                 # Servidor HTTP y API REST (Endpoints de Portafolio, SEC, Moat y Valuacion)
│   │   └── static/                   # SPA: index.html, style.css, app.js (Terminal Dual)
│   ├── visualization/
│   │   ├── financial_charts.py       # Dashboards en terminal y graficos Plotly (SEC y EPS)
│   │   └── portfolio_charts.py       # Dashboards de portafolio en terminal y HTML Plotly
│   ├── main_app.py                   # Lanza la aplicacion web del Broker & Research Terminal
│   ├── main_data_update.py           # Descarga de datos de mercado
│   ├── main_financial_history.py     # Historico 10-K/10-Q y graficos
│   ├── main_analysis.py              # CLI principal: metricas, Moat y --valuation
│   ├── main_portfolio.py             # Simulador de portafolio y paper trading
│   └── main_research_report.py       # 🚀 CLI para generar reportes institucionales de cobertura
├── config/
│   ├── watchlist.json                # Lista de activos bajo seguimiento
│   └── moat_ratings.json             # Evaluaciones cualitativas de Moat
├── data/
│   ├── cache/                        # Cache local de fundamentales, precios y SEC
│   └── portfolio/                    # Ledger inmutable de transacciones
├── exports/
│   └── charts/                       # Graficos interactivos HTML generados con Plotly
├── tests/                            # 62 tests unitarios automatizados con pytest
│   ├── test_analyzers.py
│   ├── test_moat_manager.py
│   ├── test_portfolio.py
│   ├── test_sec_extractor.py
│   ├── test_valuation.py             # Tests para los 7 modelos de valuacion
│   ├── test_visualization.py
│   ├── test_watchlist_manager.py
│   └── test_web_api.py               # Tests para endpoints REST y reportes
├── CAREER_PORTFOLIO_GUIDE.md         # 🎓 Guía de empleabilidad, LaTeX para CV y preguntas de entrevista
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Instalación y Puesta en Marcha

```powershell
# 1. Clonar el repositorio
git clone https://github.com/ronaldreighsrsc/fundamental-analysis-hub.git

# 2. Crear el entorno virtual en Windows
py -m venv venv

# 3. Activar el entorno virtual:
.\venv\Scripts\Activate.ps1
# O en CMD:
venv\Scripts\activate

# 4. Instalar las dependencias
pip install -r requirements.txt

# 5. Probar que todo funciona correctamente
python verify_setup.py
```

---

## 💡 Guía de Uso

### 1. Modelos de Valuación de Valor Intrínseco (`--valuation`)
Ejecuta la suite completa de valuación sobre cualquier ticker, generando paneles enriquecidos en consola con señales de inversión (`BUY`, `SELL`, `COMPRAR`, `VENDER`):

```powershell
# Ejecutar los 6 modelos de valuacion sobre Apple
python src/main_analysis.py --ticker AAPL --valuation

# Ejecutar sobre DaVita
python src/main_analysis.py --ticker DVA --valuation
```

#### Modelos incluidos en el reporte:
1. **Fórmula de Graham**:
   - Clásico 1962: $V = \frac{EPS \times (8.5 + 2g) \times 4.4}{Y}$
   - Conservador: $V = \frac{EPS \times (7 + 1g) \times 4.4}{Y}$
   - Rendimiento del bono corporativo AAA obtenido de FRED.
2. **WACC (Costo Promedio Ponderado de Capital)**:
   - Tasa libre de riesgo (US 10Y Treasury).
   - Costo de Equity mediante CAPM: $R_f + \beta \times (R_m - R_f)$.
   - Costo de deuda After-Tax: $\frac{\text{Intereses}}{\text{Deuda}} \times (1 - \text{Tax Rate})$.
3. **Multi-Stage DCF (5 Años)**:
   - Proyecciones de Free Cash Flow basadas en el margen operativo y margen CapEx históricos de la SEC.
   - Valor Terminal con crecimiento perpetuo al 2.5%.
   - Cálculo del Margen de Seguridad vs precio de mercado.
4. **Modelo Forward P/E (5 Años)**:
   - Crecimiento de ingresos proyectado.
   - Margen de beneficio neto histórico.
   - **Tasa anual de recompra o dilución de acciones**.
   - Forward EPS proyectado y precio objetivo a 5 años según múltiplo terminal de salida.
5. **Dividend Discount Model (DDM)**:
   - Tasa de crecimiento de dividendos histórica (CAGR).
   - Tasa de retorno requerida y valor justo por Gordon Growth.
6. **Reverse DCF (Valuación Inversa)**:
   - Revela el crecimiento anual de FCF que el precio actual del mercado descuenta.
   - Diagnóstico del riesgo de expectativas vs el crecimiento contable real auditado.
7. **Múltiplos Relativos y Comparables (PEG, P/E Mi Favorita, P/S, P/B, P/CF)**:
   - Ratio PEG de Peter Lynch ($PEG < 1.0$ infravalorada, $PEG > 2.0$ sobrevalorada).
   - Método "Mi Favorita": precio objetivo por reversión a la mediana histórica del múltiplo P/E.
   - Valoraciones específicas por Price-to-Sales (alto crecimiento), Price-to-Book (financieras/bancos) y Price-to-Cash-Flow.

---

### 2. API REST de Valuación

La plataforma expone endpoints JSON para integración con interfaces web o herramientas externas:

```bash
# Consultar todos los modelos de valuacion para un ticker
curl "http://localhost:8000/api/valuation?ticker=AAPL&model=all"

# Consultar un modelo especifico (graham, wacc, dcf, pe, ddm, reverse)
curl "http://localhost:8000/api/valuation?ticker=AAPL&model=graham"
curl "http://localhost:8000/api/valuation?ticker=AAPL&model=dcf"
curl "http://localhost:8000/api/valuation?ticker=AAPL&model=reverse"
```

---

### 3. Histórico Financiero SEC (10-K / 10-Q) y Métricas de Dilución

```powershell
# Tabla evolutiva con Basic/Diluted EPS y Shares Outstanding
python src/main_financial_history.py --ticker AAPL

# Abrir dashboard interactivo en modo oscuro con Plotly
python src/main_financial_history.py --ticker AAPL --plot

# Ver ultimos 10 anos auditados
python src/main_financial_history.py --ticker MSFT --years 10 --plot
```

---

### 4. Generador de Reportes Institucionales de Cobertura (Equity Research One-Pager)

Genera de forma automatizada informes ejecutivos de iniciación de cobertura en formato Markdown (`reports/`), combinando los 3 pilares del análisis fundamental con recomendación formal (**BUY / HOLD / SELL**) y margen de seguridad:

```powershell
# Generar reporte de cobertura para Apple (AAPL)
python src/main_research_report.py --ticker AAPL

# Generar reporte para DaVita (DVA)
python src/main_research_report.py --ticker DVA

# Generar reportes para todos los activos en watchlist
python src/main_research_report.py --all-watchlist
```

---

### 5. Terminal Web Dual: Trading Desk & Research Fundamental ($100.000 USD)

Inicia la aplicación web interactiva en modo oscuro:

```powershell
python src/main_app.py
```
Accede a `http://127.0.0.1:5000` para:
- **Pestaña Trading Desk & Portafolio**:
  - Ejecutar compras y ventas con cotizaciones en tiempo real.
  - Simular aportes mensuales DCA y monitorear la disciplina de acumulación.
  - Comparar el rendimiento de la cartera contra el S&P 500 (SPY) con cálculo de Alpha y PME.
  - Auditar el libro mayor inmutable de transacciones.
- **Pestaña Terminal de Research & Valuación (3 Pilares)**:
  - Búsqueda instantánea de cualquier ticker (`AAPL`, `KO`, `DVA`, `MSFT`, `NVDA`, `GOOGL`).
  - Tarjetas visuales de Foso Económico (Moat), Escudo de Solvencia y Detección de Dilución por Stock-Based Compensation.
  - Matriz interactiva de los 7 modelos de valuación con semáforo de margen de seguridad.
  - Botón de descarga directa del reporte de investigación en formato Markdown (`.md`).

---

### 6. Simulador de Portafolio por Línea de Comandos

```powershell
# Ver estado del portafolio, posiciones y P&L
python src/main_portfolio.py

# Simular compra
python src/main_portfolio.py --buy --ticker DVA --shares 50 --price 148.50 --fee 1.50 --notes "Tesis Moat Duopolio"

# Simular venta
python src/main_portfolio.py --sell --ticker DVA --shares 20 --price 165.00 --fee 1.50 --notes "Toma de beneficios"

# Aportes mensuales DCA
python src/main_portfolio.py --deposit 500.00 --notes "Aporte mensual"
python src/main_portfolio.py --simulate-monthly 500 --months 6
```

---

### 7. Suite de Pruebas Automatizadas (Pytest)

Ejecuta los **62 tests unitarios automatizados (100% pass rate)**:

```powershell
pytest -v
```

---

### 8. Recursos de Empleabilidad & Pitch de Entrevistas

Para candidatos a puestos de **Trainee / Junior Financial Analyst, Equity Research o FinTech**, consulta el archivo [CAREER_PORTFOLIO_GUIDE.md](CAREER_PORTFOLIO_GUIDE.md), que incluye:
- El código exacto en formato LaTeX listo para tu CV.
- Textos de impacto para LinkedIn y portafolios de GitHub.
- Playbook técnico con las 5 preguntas y respuestas clave de entrevista financiera (Reverse DCF, Dilución por SBC, Ajuste Graham FRED AAA, Heurísticas de Solvencia).

---

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.

