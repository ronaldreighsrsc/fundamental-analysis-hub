import os
import sys
import webbrowser
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

from src.portfolio.portfolio_manager import PortfolioManager
from src.portfolio.portfolio_analytics import PortfolioAnalytics

console = Console()


def _format_currency(val, decimals=2):
    """Formatea valores monetarios con comas de miles."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        return f"${val:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def _format_pct(val, decimals=2, include_sign=True):
    """Formatea valores porcentuales con estilo y color."""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        sign = "+" if val > 0 and include_sign else ""
        text = f"{sign}{val:.{decimals}f}%"
        if val > 0:
            return f"[bold green]{text}[/bold green]"
        elif val < 0:
            return f"[bold red]{text}[/bold red]"
        return text
    except (TypeError, ValueError):
        return "N/A"


def render_terminal_portfolio(manager: PortfolioManager):
    """Renderiza el dashboard completo del portafolio en consola con Rich."""
    summary = manager.get_summary()
    positions = manager.get_positions()
    analytics = PortfolioAnalytics(manager)

    # 1. Panel de Resumen Ejecutivo
    total_nav_str = _format_currency(summary["portfolio_value"])
    cash_str = f"{_format_currency(summary['cash_balance'])} ({summary['cash_weight_pct']}%)"
    invested_str = _format_currency(summary["positions_market_value"])
    unrealized_pnl_str = (
        f"{_format_currency(summary['unrealized_pnl'])} "
        f"({_format_pct((summary['unrealized_pnl'] / summary['invested_capital'] * 100) if summary['invested_capital'] > 0 else 0.0)})"
    )
    realized_pnl_str = _format_currency(summary["realized_pnl"])
    total_return_str = _format_pct(summary["total_return_pct"])
    deposits_str = _format_currency(summary["net_deposits"])

    # Metricas de Benchmark y Alpha (S&P 500 / SPY)
    bench_data = analytics.get_benchmark_comparison(benchmark_ticker="SPY")
    bench_metrics = bench_data.get("metrics", {})
    bench_ret_str = _format_pct(bench_metrics.get("benchmark_return_pct", 0.0))
    alpha_str = _format_pct(bench_metrics.get("alpha_pct", 0.0))
    bench_val_str = _format_currency(bench_metrics.get("current_benchmark_val", 0.0))

    header_text = f"""[bold yellow]VALOR TOTAL DEL PORTAFOLIO (NAV):[/bold yellow] [bold white]{total_nav_str}[/bold white]   |   [bold yellow]RENTABILIDAD CARTERA:[/bold yellow] {total_return_str}
  [bold yellow]BENCHMARK S&P 500 (SPY):[/bold yellow]          [bold white]{bench_val_str}[/bold white] ({bench_ret_str})   |   [bold yellow]ALPHA GENERADO:[/bold yellow]       {alpha_str}

  * [cyan]Efectivo Disponible:[/cyan] [bold white]{cash_str}[/bold white]     * [cyan]Capital Invertido:[/cyan] [bold white]{invested_str}[/bold white]
  * [cyan]P&L No Realizado:[/cyan]   {unrealized_pnl_str}        * [cyan]P&L Realizado Cerrado:[/cyan] [bold white]{realized_pnl_str}[/bold white]
  * [cyan]Aportaciones Netas:[/cyan] [bold white]{deposits_str}[/bold white]        * [cyan]Posiciones Abiertas:[/cyan] [bold white]{summary['positions_count']}[/bold white]
"""
    console.print(
        Panel(header_text, title="[bold green]SIMULADOR DE INVERSIONES & PORTAFOLIO[/bold green]", border_style="green")
    )
    console.print()

    # 2. Tabla de Posiciones Abiertas
    if positions:
        pos_table = Table(title="Posiciones Abiertas en Cartera", show_lines=True)
        pos_table.add_column("Ticker", style="cyan", justify="center")
        pos_table.add_column("Nombre", style="white", max_width=22)
        pos_table.add_column("Sector", style="dim", max_width=16)
        pos_table.add_column("Acciones", justify="right")
        pos_table.add_column("Costo Prom.", justify="right")
        pos_table.add_column("Precio Actual", justify="right")
        pos_table.add_column("Valor Mercado", justify="right", style="white")
        pos_table.add_column("P&L No Realizado ($)", justify="right")
        pos_table.add_column("Retorno %", justify="right")
        pos_table.add_column("Peso %", justify="right")

        for p in positions.values():
            pnl_val = p["unrealized_pnl"]
            pnl_pct = p["unrealized_pnl_pct"]
            pnl_str = f"+${pnl_val:,.2f}" if pnl_val >= 0 else f"-${abs(pnl_val):,.2f}"
            pnl_colored = f"[green]{pnl_str}[/green]" if pnl_val >= 0 else f"[red]{pnl_str}[/red]"

            pos_table.add_row(
                p["ticker"],
                p["name"],
                p["sector"],
                f"{p['shares']:.2f}",
                _format_currency(p["avg_cost"]),
                _format_currency(p["current_price"]),
                _format_currency(p["market_value"]),
                pnl_colored,
                _format_pct(pnl_pct),
                f"{p.get('weight_pct', 0.0):.1f}%",
            )

        console.print(pos_table)
        console.print()
    else:
        console.print("[yellow]No tienes posiciones abiertas actualmente. Ejecuta una compra con --buy.[/yellow]\n")

    # 3. Asignacion de Activos y Diversificacion
    allocation = analytics.get_asset_allocation()
    alloc_table = Table(title="Asignacion por Clase de Activo", show_lines=True)
    alloc_table.add_column("Clase de Activo", style="cyan")
    alloc_table.add_column("Valor ($)", justify="right")
    alloc_table.add_column("Peso %", justify="right")
    alloc_table.add_column("Distribucion Visual", justify="left")

    for item in allocation.values():
        w = item["weight_pct"]
        bars = int(round(w / 5))  # Escala 1 a 20 caracteres
        bar_str = f"[bold green]{'#' * bars}[/bold green]" if bars > 0 else "-"
        alloc_table.add_row(
            item["label"],
            _format_currency(item["market_value"]),
            f"{w:.1f}%",
            bar_str,
        )

    console.print(alloc_table)
    console.print()

    # 4. Historial Reciente de Transacciones
    history = manager.get_transaction_history()[:6]
    if history:
        tx_table = Table(title="Ultimas Transacciones Auditadas", show_lines=True)
        tx_table.add_column("Fecha/Hora", style="dim", max_width=16)
        tx_table.add_column("Tipo", justify="center")
        tx_table.add_column("Ticker", style="cyan", justify="center")
        tx_table.add_column("Acciones", justify="right")
        tx_table.add_column("Precio", justify="right")
        tx_table.add_column("Total ($)", justify="right")
        tx_table.add_column("Notas", style="dim", max_width=30)

        for tx in history:
            t_type = tx.get("type", "")
            type_badge = (
                "[bold green]COMPRA[/bold green]" if t_type == "BUY"
                else "[bold red]VENTA[/bold red]" if t_type == "SELL"
                else "[bold blue]DEPOSITO[/bold blue]" if t_type == "DEPOSIT"
                else "[bold yellow]DIVIDENDO[/bold yellow]" if t_type == "DIVIDEND"
                else t_type
            )
            dt_str = tx.get("timestamp", "")[:16].replace("T", " ")

            tx_table.add_row(
                dt_str,
                type_badge,
                tx.get("ticker", ""),
                f"{float(tx.get('shares', 0)):.2f}" if tx.get("shares") else "-",
                _format_currency(tx.get("price")) if tx.get("price") else "-",
                _format_currency(tx.get("total")),
                tx.get("notes") or "-",
            )

        console.print(tx_table)
        console.print()


def create_portfolio_dashboard(
    manager: PortfolioManager,
    output_path: Optional[str] = None,
    auto_open: bool = True,
    benchmark_ticker: str = "SPY",
) -> str:
    """
    Genera un dashboard interactivo Plotly exportado a HTML con:
    - 1. Grafico de Evolucion Temporal: NAV vs Aportaciones Acumuladas vs S&P 500 (SPY).
    - 2. Donut chart de Asignacion por Clase de Activo.
    - 3. Donut chart de Distribucion por Sector.
    - 4. Bar chart de Posiciones coloreadas por P&L %.
    - 5. Bar chart de Ponderacion en Cartera (%).
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    summary = manager.get_summary()
    positions = manager.get_positions()
    analytics = PortfolioAnalytics(manager)

    allocation = analytics.get_asset_allocation()
    sectors = analytics.get_sector_distribution()

    # Obtener comparativa de evolucion y benchmark
    bench_data = analytics.get_benchmark_comparison(benchmark_ticker=benchmark_ticker)
    tl = bench_data.get("timeline", {})
    t_dates = tl.get("dates", [])
    nav_series = tl.get("portfolio_nav", [])
    deposits_series = tl.get("cumulative_deposits", [])
    bench_series = tl.get("benchmark_nav", [])
    bench_metrics = bench_data.get("metrics", {})
    alpha_val = bench_metrics.get("alpha_pct", 0.0)

    alpha_str = f"+{alpha_val:.2f}%" if alpha_val >= 0 else f"{alpha_val:.2f}%"

    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            f"<b>1. Evolucion Temporal: NAV vs Aportes Acumulados vs Benchmark {benchmark_ticker} (Alpha: {alpha_str})</b>",
            None,
            "<b>2. Asignacion por Clase de Activo</b>",
            "<b>3. Distribucion Sectorial del Capital</b>",
            "<b>4. P&L No Realizado por Posicion (%)</b>",
            "<b>5. Ponderacion en Cartera (%)</b>",
        ),
        specs=[
            [{"type": "xy", "colspan": 2}, None],
            [{"type": "domain"}, {"type": "domain"}],
            [{"type": "xy"}, {"type": "xy"}],
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.10,
    )

    # 1. Grafico de Lineas de Evolucion Temporal y Benchmark
    if t_dates:
        # Aportes acumulados (Capital puesto por el inversor)
        fig.add_trace(
            go.Scatter(
                x=t_dates,
                y=deposits_series,
                mode="lines+markers",
                name="Aportes Acumulados ($)",
                line=dict(color="#94a3b8", width=2, dash="dot"),
                marker=dict(size=4),
                hovertemplate="<b>Aportaciones Acumuladas:</b> $%{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Benchmark S&P 500 (SPY PME)
        fig.add_trace(
            go.Scatter(
                x=t_dates,
                y=bench_series,
                mode="lines+markers",
                name=f"Benchmark S&P 500 ({benchmark_ticker})",
                line=dict(color="#f59e0b", width=2.5),
                marker=dict(size=4),
                hovertemplate=f"<b>Benchmark {benchmark_ticker}:</b> $%{{y:,.2f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Valor Total del Portafolio (NAV)
        fig.add_trace(
            go.Scatter(
                x=t_dates,
                y=nav_series,
                mode="lines+markers",
                name="Valor Portafolio (NAV)",
                line=dict(color="#06b6d4", width=3),
                marker=dict(size=5),
                fill="tonexty",
                fillcolor="rgba(6, 182, 212, 0.08)",
                hovertemplate="<b>Valor Cartera (NAV):</b> $%{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # 2. Donut Clase de Activo
    alloc_labels = [item["label"] for item in allocation.values() if item["market_value"] > 0]
    alloc_values = [item["market_value"] for item in allocation.values() if item["market_value"] > 0]
    if alloc_values:
        fig.add_trace(
            go.Pie(
                labels=alloc_labels,
                values=alloc_values,
                hole=0.45,
                textinfo="label+percent",
                marker=dict(colors=["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#64748b"]),
            ),
            row=2,
            col=1,
        )

    # 3. Donut Sectores
    sec_labels = list(sectors.keys())
    sec_values = [s["market_value"] for s in sectors.values()]
    if sec_values:
        fig.add_trace(
            go.Pie(
                labels=sec_labels,
                values=sec_values,
                hole=0.45,
                textinfo="label+percent",
            ),
            row=2,
            col=2,
        )

    # 4. Bar Chart P&L % por Posicion
    if positions:
        pos_tickers = list(positions.keys())
        pnl_pcts = [p["unrealized_pnl_pct"] for p in positions.values()]
        bar_colors = ["#10b981" if v >= 0 else "#ef4444" for v in pnl_pcts]

        fig.add_trace(
            go.Bar(
                x=pos_tickers,
                y=pnl_pcts,
                marker_color=bar_colors,
                hovertemplate="<b>%{x}</b>: %{y:.2f}%<extra></extra>",
                name="P&L (%)",
            ),
            row=3,
            col=1,
        )

        # 5. Bar Chart Pesos en Cartera
        weights = [p.get("weight_pct", 0.0) for p in positions.values()]
        fig.add_trace(
            go.Bar(
                x=pos_tickers,
                y=weights,
                marker_color="#6366f1",
                hovertemplate="<b>%{x}</b>: %{y:.1f}% del portafolio<extra></extra>",
                name="Peso (%)",
            ),
            row=3,
            col=2,
        )

    # Estilos dark de alta gama
    total_nav_fmt = _format_currency(summary["portfolio_value"])
    total_ret_fmt = _format_pct(summary["total_return_pct"])
    bench_ret_fmt = _format_pct(bench_metrics.get("benchmark_return_pct", 0.0))

    fig.update_layout(
        title=dict(
            text=f"<b>Dashboard de Portafolio & Paper Trading</b> — NAV: {total_nav_fmt} ({total_ret_fmt}) | S&P 500: {bench_ret_fmt} | Alpha: {alpha_str}",
            font=dict(size=19, color="#f8fafc"),
            x=0.03,
            y=0.98,
        ),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(family="Segoe UI, Inter, sans-serif", color="#cbd5e1"),
        height=1150,
        margin=dict(l=50, r=50, t=110, b=50),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=0.98,
            font=dict(size=11),
        ),
    )

    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        charts_dir = os.path.join(base_dir, "exports", "charts")
        os.makedirs(charts_dir, exist_ok=True)
        output_path = os.path.join(charts_dir, "portfolio_dashboard.html")
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

