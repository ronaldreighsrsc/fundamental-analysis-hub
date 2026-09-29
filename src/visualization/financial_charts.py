import sys
import os
import webbrowser
import pandas as pd
import numpy as np
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def _format_currency(val, decimals=2):
    """Formatea valores monetarios en miles de millones (B) o millones (M)."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1_000_000_000:
            return f"${val / 1_000_000_000:.{decimals}f}B"
        if abs(val) >= 1_000_000:
            return f"${val / 1_000_000:.{decimals}f}M"
        return f"${val:.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def _format_pct(val, decimals=1, include_sign=False):
    """Formatea valores porcentuales con color segun signo si se especifica."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        val = float(val)
        sign = "+" if val > 0 and include_sign else ""
        text = f"{sign}{val:.{decimals}f}%"
        if include_sign:
            if val > 0:
                return f"[green]{text}[/green]"
            elif val < 0:
                return f"[red]{text}[/red]"
        return text
    except (TypeError, ValueError):
        return "N/A"


def _format_shares(val, decimals=2):
    """Formatea la cantidad de acciones en Billions (B), Millions (M) o unidades."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1_000_000_000:
            return f"{val / 1_000_000_000:.{decimals}f}B"
        if abs(val) >= 1_000_000:
            return f"{val / 1_000_000:.{decimals}f}M"
        return f"{val:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def _format_eps(val, decimals=2):
    """Formatea EPS como valor por accion ($X.XX)."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        val = float(val)
        return f"${val:.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def render_terminal_per_share_table(ticker: str, df: pd.DataFrame, company_name: str = ""):
    """
    Muestra en terminal una tabla dedicada a la evolucion de metricas por accion y estructura de capital:
    Basic EPS, Diluted EPS, Basic Shares, Diluted Shares, YoY %, spread de dilucion y grafico ASCII de EPS.
    """
    if df.empty:
        return

    # Comprobar si al menos hay EPS o acciones disponibles
    cols_check = ["eps_basic", "eps_diluted", "shares_basic", "shares_diluted"]
    available_cols = [c for c in cols_check if c in df.columns]
    if not available_cols:
        return

    mask = pd.Series(False, index=df.index)
    for col in available_cols:
        mask = mask | df[col].notnull()

    df_clean = df[mask].copy()
    if df_clean.empty:
        return

    title_text = f"Métricas por Acción & Estructura de Capital: {ticker}"
    if company_name:
        title_text += f" - {company_name}"

    table = Table(title=title_text, show_lines=True)
    table.add_column("Periodo", style="cyan", justify="center")
    table.add_column("EPS Basic", style="white", justify="right")
    table.add_column("EPS Diluted", style="bold white", justify="right")
    table.add_column("YoY EPS %", justify="right")
    table.add_column("Basic Shares", style="white", justify="right")
    table.add_column("Diluted Shares", style="magenta", justify="right")
    table.add_column("YoY Acc. %", justify="right")
    table.add_column("Spread Dil. %", justify="right")
    table.add_column("Evolución EPS Dil. (Gráfico)", style="cyan", justify="left")

    # Escalar barra grafica con el maximo EPS diluido positivo
    max_eps = 1.0
    if "eps_diluted" in df_clean.columns and (df_clean["eps_diluted"] > 0).any():
        max_eps = df_clean["eps_diluted"].max()
    elif "eps_basic" in df_clean.columns and (df_clean["eps_basic"] > 0).any():
        max_eps = df_clean["eps_basic"].max()

    bar_max_width = 16

    for idx, row in df_clean.iterrows():
        eps_b = row.get("eps_basic")
        eps_d = row.get("eps_diluted")
        eps_growth = (
            row.get("eps_diluted_growth_yoy")
            if "eps_diluted_growth_yoy" in row and not pd.isna(row.get("eps_diluted_growth_yoy"))
            else row.get("eps_basic_growth_yoy")
        )

        sh_b = row.get("shares_basic")
        sh_d = row.get("shares_diluted")
        sh_growth = (
            row.get("shares_diluted_change_yoy")
            if "shares_diluted_change_yoy" in row and not pd.isna(row.get("shares_diluted_change_yoy"))
            else row.get("shares_basic_change_yoy")
        )
        spread = row.get("dilution_spread_pct")

        eps_b_str = _format_eps(eps_b)
        eps_d_str = _format_eps(eps_d)
        eps_growth_str = _format_pct(eps_growth, decimals=1, include_sign=True)

        sh_b_str = _format_shares(sh_b)
        sh_d_str = _format_shares(sh_d)

        # En acciones: crecimiento negativo es recompras/buybacks (verde), positivo es dilucion (rojo)
        sh_growth_str = "N/A"
        if sh_growth is not None and not pd.isna(sh_growth):
            sign = "+" if sh_growth > 0 else ""
            txt = f"{sign}{sh_growth:.1f}%"
            if sh_growth < -0.05:
                sh_growth_str = f"[green]{txt}[/green]"
            elif sh_growth > 0.05:
                sh_growth_str = f"[red]{txt}[/red]"
            else:
                sh_growth_str = txt

        spread_str = _format_pct(spread, decimals=2)

        # Generar barra grafica proporcional para EPS
        target_val = eps_d if (eps_d is not None and not pd.isna(eps_d)) else eps_b
        if target_val and not pd.isna(target_val) and target_val > 0 and max_eps > 0:
            filled_len = int(round((target_val / max_eps) * bar_max_width))
            filled_len = max(1, min(filled_len, bar_max_width))
            bar_graph = f"[bold cyan]{'#' * filled_len}[/bold cyan]"
        elif target_val and not pd.isna(target_val) and target_val < 0:
            bar_graph = "[bold red]NEGATIVO[/bold red]"
        else:
            bar_graph = "-"

        table.add_row(
            str(idx),
            eps_b_str,
            eps_d_str,
            eps_growth_str,
            sh_b_str,
            sh_d_str,
            sh_growth_str,
            spread_str,
            bar_graph,
        )

    console.print(table)
    console.print()


def render_terminal_financial_table(ticker: str, df: pd.DataFrame, company_name: str = ""):
    """
    Muestra en terminal una tabla con la evolucion multianual de las finanzas de la empresa,
    incluyendo barras graficas proporcionales en ASCII para visualizar el crecimiento de ingresos,
    y a continuacion la tabla complementaria de metricas por accion y capital (EPS y Shares).
    """
    if df.empty:
        console.print(f"[yellow]No hay datos historicos disponibles para {ticker}.[/yellow]")
        return

    # Filtrar solo anios con al menos ingresos o beneficios
    valid_mask = df.get("revenue", pd.Series(dtype=float)).notnull() | df.get("net_income", pd.Series(dtype=float)).notnull()
    df_clean = df[valid_mask].copy()

    if df_clean.empty:
        console.print(f"[yellow]No hay estados financieros validos para mostrar para {ticker}.[/yellow]")
        return

    title_text = f"Historico Financiero Multianual (10-K SEC): {ticker}"
    if company_name:
        title_text += f" - {company_name}"

    table = Table(title=title_text, show_lines=True)
    table.add_column("Periodo", style="cyan", justify="center")
    table.add_column("Ventas", style="white", justify="right")
    table.add_column("YoY %", justify="right")
    table.add_column("Mg. Bruto", justify="right")
    table.add_column("Mg. Op.", justify="right")
    table.add_column("Net Income", style="white", justify="right")
    table.add_column("Mg. Neto", justify="right")
    table.add_column("FCF", style="white", justify="right")
    table.add_column("Mg. FCF", justify="right")
    table.add_column("Evolucion Ventas (Grafico)", style="green", justify="left")

    # Calcular valor maximo de ingresos para escalar la barra grafica
    max_rev = df_clean["revenue"].max() if "revenue" in df_clean.columns and df_clean["revenue"].max() > 0 else 1.0
    bar_max_width = 16  # Caracteres de ancho de barra

    for idx, row in df_clean.iterrows():
        rev = row.get("revenue")
        rev_str = _format_currency(rev)
        yoy_str = _format_pct(row.get("revenue_growth_yoy"), decimals=1, include_sign=True)
        gm_str = _format_pct(row.get("gross_margin_pct"), decimals=1)
        om_str = _format_pct(row.get("operating_margin_pct"), decimals=1)
        ni_str = _format_currency(row.get("net_income"))
        nm_str = _format_pct(row.get("net_margin_pct"), decimals=1)
        fcf_str = _format_currency(row.get("free_cash_flow"))
        fcf_m_str = _format_pct(row.get("fcf_margin_pct"), decimals=1)

        # Generar barra grafica proporcional
        if rev and not pd.isna(rev) and rev > 0:
            filled_len = int(round((rev / max_rev) * bar_max_width))
            filled_len = max(1, min(filled_len, bar_max_width))
            bar_graph = f"[bold green]{'#' * filled_len}[/bold green]"
        else:
            bar_graph = "-"

        table.add_row(
            str(idx),
            rev_str,
            yoy_str,
            gm_str,
            om_str,
            ni_str,
            nm_str,
            fcf_str,
            fcf_m_str,
            bar_graph,
        )

    console.print()
    console.print(table)
    console.print()

    # Mostrar la tabla complementaria de metricas por accion y estructura de capital
    render_terminal_per_share_table(ticker, df, company_name)


def create_financial_history_chart(
    ticker: str,
    df: pd.DataFrame,
    company_name: str = "",
    output_path: Optional[str] = None,
    auto_open: bool = True,
) -> str:
    """
    Genera un dashboard interactivo multianual con Plotly y lo exporta a HTML.
    Consta de 6 paneles de analisis financiero profundo (3 filas x 2 columnas):
      1. Ventas y Beneficio Neto ($B) + Margen Neto % (Eje secundario).
      2. Calidad de Ganancias: Flujo de Caja Libre (FCF) vs Beneficio Neto.
      3. Evolucion de Margenes (% Bruto, % Operativo, % FCF) para verificar el Moat.
      4. Beneficio por Accion (Basic EPS vs Diluted EPS) + Crecimiento YoY EPS Diluido (Eje secundario).
      5. Estructura de Acciones: Basic vs Diluted Shares (M) + Area de Dilucion.
      6. Variacion Interanual YoY (%): Crecimiento EPS Diluido vs Recompras/Dilucion de Acciones.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if df.empty:
        raise ValueError(f"No hay datos para graficar para {ticker}")

    # Filtrar datos validos (que tengan al menos ingresos, beneficio, EPS o acciones)
    mask = pd.Series(False, index=df.index)
    for col in ["revenue", "net_income", "eps_basic", "eps_diluted", "shares_diluted", "shares_basic"]:
        if col in df.columns:
            mask = mask | df[col].notnull()
    df_clean = df[mask].copy()

    if df_clean.empty:
        raise ValueError(f"No hay periodos con datos financieros validos para graficar para {ticker}")

    periods = [str(p) for p in df_clean.index]
    rev_in_b = df_clean.get("revenue", pd.Series(0, index=df_clean.index)) / 1e9
    ni_in_b = df_clean.get("net_income", pd.Series(0, index=df_clean.index)) / 1e9
    fcf_in_b = df_clean.get("free_cash_flow", pd.Series(0, index=df_clean.index)) / 1e9
    shares_b_in_m = df_clean.get("shares_basic", pd.Series(0, index=df_clean.index)) / 1e6
    shares_d_in_m = df_clean.get("shares_diluted", pd.Series(0, index=df_clean.index)) / 1e6
    eps_b = df_clean.get("eps_basic", pd.Series(np.nan, index=df_clean.index))
    eps_d = df_clean.get("eps_diluted", pd.Series(np.nan, index=df_clean.index))
    eps_d_yoy = df_clean.get("eps_diluted_growth_yoy", pd.Series(np.nan, index=df_clean.index))
    shares_d_yoy = df_clean.get("shares_diluted_change_yoy", pd.Series(np.nan, index=df_clean.index))

    # Crear figura con 6 subplots (3 filas x 2 columnas)
    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            "<b>1. Ingresos y Beneficio Neto ($B) + Margen Neto</b>",
            "<b>2. Calidad de Caja: FCF vs Beneficio Neto ($B)</b>",
            "<b>3. Evolución de Márgenes (%) - Salud del Moat</b>",
            "<b>4. Beneficio por Acción (EPS) y Crecimiento YoY (%)</b>",
            "<b>5. Estructura de Capital: Basic vs Diluted Shares (M)</b>",
            "<b>6. Variación Interanual YoY (%): EPS vs Recompras/Dilución</b>",
        ),
        specs=[
            [{"secondary_y": True}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": True}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    # -------------------------------------------------------------------------
    # Panel 1: Ventas y Beneficio Neto + Margen Neto (secundario)
    # -------------------------------------------------------------------------
    fig.add_trace(
        go.Bar(
            x=periods,
            y=rev_in_b,
            name="Ventas ($B)",
            marker_color="#3b82f6",
            hovertemplate="<b>Ventas:</b> $%{y:.2f}B<extra></extra>",
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=periods,
            y=ni_in_b,
            name="Beneficio Neto ($B)",
            marker_color="#10b981",
            hovertemplate="<b>Beneficio Neto:</b> $%{y:.2f}B<extra></extra>",
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    if "net_margin_pct" in df_clean.columns and df_clean["net_margin_pct"].notnull().any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=df_clean["net_margin_pct"],
                name="Margen Neto (%)",
                mode="lines+markers",
                line=dict(color="#f59e0b", width=2.5),
                marker=dict(size=5),
                hovertemplate="<b>Margen Neto:</b> %{y:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
            secondary_y=True,
        )

    # -------------------------------------------------------------------------
    # Panel 2: FCF vs Net Income
    # -------------------------------------------------------------------------
    fig.add_trace(
        go.Bar(
            x=periods,
            y=fcf_in_b,
            name="Free Cash Flow ($B)",
            marker_color="#06b6d4",
            hovertemplate="<b>FCF:</b> $%{y:.2f}B<extra></extra>",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=periods,
            y=ni_in_b,
            name="Net Income ($B)",
            mode="lines+markers",
            line=dict(color="#10b981", width=2, dash="dash"),
            marker=dict(size=5),
            hovertemplate="<b>Net Income:</b> $%{y:.2f}B<extra></extra>",
        ),
        row=1,
        col=2,
    )

    # -------------------------------------------------------------------------
    # Panel 3: Evolucion de Margenes (% Bruto, % Operativo, % FCF)
    # -------------------------------------------------------------------------
    if "gross_margin_pct" in df_clean.columns and df_clean["gross_margin_pct"].notnull().any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=df_clean["gross_margin_pct"],
                name="Margen Bruto (%)",
                mode="lines+markers",
                line=dict(color="#818cf8", width=2.2),
                marker=dict(size=4),
                hovertemplate="<b>Margen Bruto:</b> %{y:.1f}%<extra></extra>",
            ),
            row=2,
            col=1,
        )
    if "operating_margin_pct" in df_clean.columns and df_clean["operating_margin_pct"].notnull().any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=df_clean["operating_margin_pct"],
                name="Margen Operativo (%)",
                mode="lines+markers",
                line=dict(color="#a855f7", width=2.2),
                marker=dict(size=4),
                hovertemplate="<b>Margen Op.:</b> %{y:.1f}%<extra></extra>",
            ),
            row=2,
            col=1,
        )
    if "fcf_margin_pct" in df_clean.columns and df_clean["fcf_margin_pct"].notnull().any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=df_clean["fcf_margin_pct"],
                name="Margen FCF (%)",
                mode="lines+markers",
                line=dict(color="#06b6d4", width=2.2),
                marker=dict(size=4),
                hovertemplate="<b>Margen FCF:</b> %{y:.1f}%<extra></extra>",
            ),
            row=2,
            col=1,
        )

    # -------------------------------------------------------------------------
    # Panel 4: Beneficio por Accion (Basic vs Diluted EPS) + Crecimiento YoY (%)
    # -------------------------------------------------------------------------
    if eps_b.notnull().any():
        fig.add_trace(
            go.Bar(
                x=periods,
                y=eps_b,
                name="Basic EPS ($)",
                marker_color="#6366f1",
                hovertemplate="<b>Basic EPS:</b> $%{y:.2f}<extra></extra>",
            ),
            row=2,
            col=2,
            secondary_y=False,
        )
    if eps_d.notnull().any():
        fig.add_trace(
            go.Bar(
                x=periods,
                y=eps_d,
                name="Diluted EPS ($)",
                marker_color="#8b5cf6",
                hovertemplate="<b>Diluted EPS:</b> $%{y:.2f}<extra></extra>",
            ),
            row=2,
            col=2,
            secondary_y=False,
        )
    if eps_d_yoy.notnull().any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=eps_d_yoy,
                name="YoY EPS Diluido (%)",
                mode="lines+markers",
                line=dict(color="#ec4899", width=2.5),
                marker=dict(size=5, symbol="diamond"),
                hovertemplate="<b>YoY EPS Diluido:</b> %{y:.1f}%<extra></extra>",
            ),
            row=2,
            col=2,
            secondary_y=True,
        )

    # -------------------------------------------------------------------------
    # Panel 5: Estructura de Capital: Basic vs Diluted Shares (M)
    # -------------------------------------------------------------------------
    if shares_b_in_m.notnull().any() and (shares_b_in_m > 0).any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=shares_b_in_m,
                name="Basic Shares (M)",
                mode="lines+markers",
                line=dict(color="#38bdf8", width=2.5),
                marker=dict(size=5),
                hovertemplate="<b>Basic Shares:</b> %{y:.1f}M<extra></extra>",
            ),
            row=3,
            col=1,
        )
    if shares_d_in_m.notnull().any() and (shares_d_in_m > 0).any():
        fig.add_trace(
            go.Scatter(
                x=periods,
                y=shares_d_in_m,
                name="Diluted Shares (M)",
                mode="lines+markers",
                fill="tonexty" if (shares_b_in_m > 0).any() else "tozeroy",
                fillcolor="rgba(244, 63, 94, 0.18)",
                line=dict(color="#f43f5e", width=2.5),
                marker=dict(size=5),
                hovertemplate="<b>Diluted Shares:</b> %{y:.1f}M<extra></extra>",
            ),
            row=3,
            col=1,
        )

    # -------------------------------------------------------------------------
    # Panel 6: Variacion Interanual YoY (%): EPS Diluido vs Recompras/Dilucion
    # -------------------------------------------------------------------------
    if eps_d_yoy.notnull().any():
        fig.add_trace(
            go.Bar(
                x=periods,
                y=eps_d_yoy,
                name="Crecimiento EPS (%)",
                marker_color="#10b981",
                hovertemplate="<b>Crecimiento EPS:</b> %{y:.1f}%<extra></extra>",
            ),
            row=3,
            col=2,
        )
    if shares_d_yoy.notnull().any():
        fig.add_trace(
            go.Bar(
                x=periods,
                y=shares_d_yoy,
                name="Variación Acciones (%)",
                marker_color="#f59e0b",
                hovertemplate="<b>Variación Acciones:</b> %{y:.1f}%<extra></extra>",
            ),
            row=3,
            col=2,
        )

    # Configuracion de Disenio Dark Premium
    title_main = f"<b>{ticker}</b> — Evolución Financiera y Métricas por Acción (10-K SEC EDGAR)"
    if company_name:
        title_main = f"<b>{company_name} ({ticker})</b> — Evolución Financiera y Métricas por Acción (10-K SEC EDGAR)"

    fig.update_layout(
        title=dict(
            text=title_main,
            font=dict(size=20, color="#f8fafc"),
            x=0.03,
            y=0.985,
        ),
        template="plotly_dark",
        paper_bgcolor="#0f172a",  # Fondo azul marino profundo
        plot_bgcolor="#1e293b",   # Fondo de paneles
        font=dict(family="Segoe UI, Inter, sans-serif", color="#cbd5e1"),
        height=1200,
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.015,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(30, 41, 59, 0.7)",
            bordercolor="#334155",
            borderwidth=1,
        ),
        margin=dict(l=50, r=50, t=95, b=50),
    )

    # Ajustes de ejes
    fig.update_xaxes(showgrid=True, gridcolor="#334155", zerolinecolor="#475569")
    fig.update_yaxes(showgrid=True, gridcolor="#334155", zerolinecolor="#475569")

    # Directorio de salida
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        charts_dir = os.path.join(base_dir, "exports", "charts")
        os.makedirs(charts_dir, exist_ok=True)
        output_path = os.path.join(charts_dir, f"{ticker}_financial_history.html")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fig.write_html(output_path, include_plotlyjs=True, full_html=True)

    if auto_open:
        try:
            abs_url = f"file:///{os.path.abspath(output_path).replace(os.sep, '/')}"
            webbrowser.open(abs_url)
        except Exception:
            pass

    return output_path
