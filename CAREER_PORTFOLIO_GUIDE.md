# 🎓 GUÍA DE EMPLEABILIDAD & PITCH DE ENTREVISTAS
## Proyecto: Fundamental Analysis Hub — Institutional Equity Research & Valuation Engine
**Candidato:** Ronald Solares Chuquera — Ingeniero Civil Industrial  
**Target Roles:** Trainee / Junior Financial Analyst, Equity Research Associate, Quantitative Analyst, Business Analyst (FinTech / Banca de Inversión / Asset Management).

---

## 1. Bloque en Formato LaTeX para tu Currículum Vitae (CV)

Copia y pega este bloque directamente en tu documento `.tex` o en tu archivo Overleaf, en la sección de **Proyectos Destacados**, reemplazando la versión anterior:

```latex
\textbf{\href{https://github.com/ronaldreighsrsc/fundamental-analysis-hub}{Fundamental Analysis Hub: Motor Cuantitativo de Equity Research y Valuación}} \hfill Python, SEC EDGAR API, FRED API, JavaScript, REST API
\textit{Pipeline ETL de Estados Financieros (10-K/10-Q), Suite Multi-Modelo de Valor Intrínseco y Benchmarking PME}
\begin{itemize}[noitemsep, topsep=2pt, partopsep=0pt, parsep=0pt]
    \item \textbf{Ingesta y Auditoría Contable Automatizada (SEC EDGAR):} Diseñé un pipeline ETL directo con la API pública de la SEC para procesar estados financieros históricos (10-K y 10-Q en taxonomía US-GAAP), computando heurísticas de solvencia (\textit{Current Ratio}, Caja Neta vs Deuda, Cobertura de Intereses) y detección de dilución accionaria por compensación en acciones (SBC).
    \item \textbf{Suite de Valuación Intrínseca Multi-Modelo:} Implementé 7 modelos cuantitativos de valoración: Graham 1974 (vinculado en tiempo real a la curva de bonos AAA de la Reserva Federal - FRED), DCF multi-etapa a 5 años, Forward P/E ajustado por recompras, DDM (Gordon), y Reverse DCF mediante optimización por bisección para estimar el crecimiento de flujo de caja que descuenta el mercado.
    \item \textbf{Terminal Web Interactiva y Generador de Reportes:} Construí una SPA analítica en JavaScript/CSS y un motor de generación de reportes ejecutivos (\textit{Equity Research Tear-Sheets}) que emite recomendaciones institucionales (\textit{BUY / HOLD / SELL}) con margen de seguridad, respaldado por 62 pruebas unitarias automatizadas (\textit{100\% pass rate}).
\end{itemize}
```

---

## 2. Descripción Corta para LinkedIn / GitHub Pin / Portfolio

> **Fundamental Analysis Hub** — *Plataforma institucional de análisis fundamental y valoración financiera para renta variable estadounidense.*
> - Conecta directamente a la API de la SEC EDGAR para extraer más de 15 años de informes 10-K y 10-Q auditados.
> - Evalúa la solvencia corporativa (Current Ratio, Cobertura de Intereses) y audita la dilución por Stock-Based Compensation (SBC).
> - Suite de 7 modelos de valor intrínseco: Graham 1974 (con bonos AAA de la Reserva Federal), DCF 5 años, Forward P/E, Gordon DDM, y Reverse DCF.
> - Incluye un generador automatizado de reportes de cobertura institucional (*Equity Research One-Pagers*) y una terminal web interactiva con benchmarking Alpha contra el S&P 500 (PME).
> - 62 tests automatizados con pytest (`100% pass rate`) bajo arquitectura modular y principios SOLID.

---

## 3. Playbook de Entrevista Técnica: Preguntas Clave y Cómo Defenderlas

En una entrevista para Trainee o Junior Analyst, los entrevistadores no buscan solo alguien que programe, sino alguien que **comprenda a fondo las finanzas corporativas y la contabilidad detrás del código**.

### Pregunta 1: "¿Por qué utilizas Reverse DCF (Valuación Inversa) además del DCF tradicional?"
* **Respuesta recomendada:**  
  *"El DCF tradicional es altamente sensible a los supuestos: si varías la tasa de descuento (WACC) o el crecimiento terminal en solo 1%, el valor justo puede fluctuar un 30% o más (el dilema de 'Garbage In, Garbage Out'). Por eso implementé el Reverse DCF: en lugar de adivinar el futuro, uso un algoritmo de búsqueda numérica (bisección) para despejar qué tasa de crecimiento compuesto (CAGR) de Free Cash Flow está descontando el precio actual de la acción. Así, como analista no tengo que predecir el futuro exacto, sino contrastar esa expectativa del mercado contra el crecimiento histórico auditado de la SEC para identificar asimetrías de riesgo/retorno."*

---

### Pregunta 2: "¿Cómo detectas y corriges la dilución por compensación en acciones (Stock-Based Compensation - SBC)?"
* **Respuesta recomendada:**  
  *"Muchas empresas tecnológicas inflan su Free Cash Flow porque el SBC se suma de vuelta al Flujo de Caja Operativo al ser un gasto no monetario en el corto plazo. Sin embargo, en la práctica diluye a los accionistas existentes. En mi extractor de la SEC, comparo el Weighted Average Diluted Shares año contra año y calculo el 'Dilution Spread' entre acciones básicas y diluidas. En el modelo Forward P/E, proyecto explícitamente la evolución del número de acciones: si una empresa recompra agresivamente acciones (como Apple), el EPS crece más rápido que las ventas; pero si diluye sistemáticamente para pagar a sus directivos, el valor real por acción se reduce."*

---

### Pregunta 3: "¿Por qué utilizas la fórmula de Benjamin Graham de 1974 y no solo la clásica de 1962?"
* **Respuesta recomendada:**  
  *"La fórmula clásica de 1962 ($V = EPS \times (8.5 + 2g)$) asumía un entorno con tasas de interés corporativas de referencia del 4.4% de los años 60. En 1974, ante la inflación y la subida de tipos, Graham añadió el factor multiplicador $\frac{4.4}{Y}$, donde $Y$ es el rendimiento actual de los bonos corporativos AAA. En mi proyecto, conecté la API de la Reserva Federal (FRED) para traer en tiempo real la serie mensual `AAA`, lo que permite que el valor intrínseco se contraiga automáticamente cuando los tipos de interés suben y el coste de oportunidad del capital aumenta."*

---

### Pregunta 4: "¿Cómo auditas la solvencia y la liquidez de una empresa en tu pipeline?"
* **Respuesta recomendada:**  
  *"Aplico una triple heurística de balance antes de emitir cualquier recomendación:*
  1. *Current Ratio ($Current Assets / Current Liabilities$) con umbral de seguridad $> 1.2x$ para garantizar cobertura de obligaciones operativas a 12 meses.*
  2. *Posición Neta de Caja ($\text{Caja y Equivalentes} - \text{Deuda Total}$): si la caja neta es positiva, la empresa cuenta con inmunidad de quiebra y escudo anticrisis.*
  3. *Interest Coverage Ratio ($EBIT / Gastos por Intereses$): si está por debajo de 3x, encendemos una alerta de estrés financiero ante un eventual encarecimiento del crédito."*

---

### Pregunta 5: "¿Cómo garantizaste la robustez del software?"
* **Respuesta recomendada:**  
  *"Estructuré el sistema bajo principios SOLID, utilizando Factory Pattern para tipificar instrumentos (Equities, REITs con métricas FFO/AFFO, ETFs con ratios de gastos) y un motor contable inmutable de Event-Sourcing Ledger. Todo el sistema cuenta con 62 pruebas unitarias continuas con Pytest que garantizan un 100% de tasa de aprobación en cálculos matemáticos, parsing de SEC EDGAR y endpoints REST."*
