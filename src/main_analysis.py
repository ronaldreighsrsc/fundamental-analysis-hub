import sys
import os
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Asegurar que el modulo src sea importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.watchlist_manager import WatchlistManager
from src.data.downloader import FinancialDataDownloader
from src.analysis.analyzer_factory import AnalyzerFactory
from src.analysis.moat_manager import MoatManager

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def format_number(value, decimals=2, prefix="", suffix="", multiply=1):
    """Formatea un numero para mostrar en tabla. Retorna 'N/A' si es None."""
    if value is None:
        return "N/A"
    try:
        val = float(value) * multiply
        if abs(val) >= 1_000_000_000:
            return f"{prefix}{val / 1_000_000_000:.1f}B{suffix}"
        if abs(val) >= 1_000_000:
            return f"{prefix}{val / 1_000_000:.1f}M{suffix}"
        return f"{prefix}{val:.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def format_pct(value, decimals=2):
    """Formatea un valor decimal como porcentaje."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_pct_raw(value, decimals=2):
    """Formatea un valor que ya viene como porcentaje (ej. 5.1 = 5.1%)."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


import pandas as pd
from datetime import datetime


def calculate_ytd(ticker: str) -> float:
    """Calcula el retorno YTD (Year-To-Date) usando los precios de cierre diarios en cache."""
    ticker_clean = ticker.strip().upper().replace("-", "_")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    price_path = os.path.join(base_dir, "data", "cache", f"{ticker_clean}_prices.csv")

    if not os.path.exists(price_path):
        return None

    try:
        df = pd.read_csv(price_path)
        if df.empty or "Date" not in df.columns or "Close" not in df.columns:
            return None

        # Parsear fecha sin zonas horarias locales para simplificar la comparacion
        df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)
        df = df.sort_values("Date")

        current_year = datetime.now().year
        df_year = df[df["Date"].dt.year == current_year]

        if df_year.empty:
            latest_year = df["Date"].dt.year.max()
            df_year = df[df["Date"].dt.year == latest_year]

        if df_year.empty:
            return None

        first_price = df_year.iloc[0]["Close"]
        last_price = df_year.iloc[-1]["Close"]

        if first_price == 0:
            return None

        return (last_price - first_price) / first_price
    except Exception:
        return None


# =============================================================================
# Tablas por tipo de activo
# =============================================================================

def show_equity_table(items):
    """Muestra tablas resumen para acciones (equities), divididas en dos para legibilidad."""

    # --- Tabla 1: Valoracion ---
    t1 = Table(title="Acciones - Valoracion", show_lines=True)
    t1.add_column("Ticker", style="cyan", justify="center")
    t1.add_column("Nombre", style="white", max_width=20)
    t1.add_column("Precio", style="green", justify="right")
    t1.add_column("YTD", justify="right")
    t1.add_column("Mkt Cap", justify="right")
    t1.add_column("P/E", justify="right")
    t1.add_column("PEG", justify="right")
    t1.add_column("Div Yield", justify="right")
    t1.add_column("Payout", justify="right")

    # --- Tabla 2: Rentabilidad, Salud e Inversores ---
    t2 = Table(title="Acciones - Rentabilidad, Salud e Inversores", show_lines=True)
    t2.add_column("Ticker", style="cyan", justify="center")
    t2.add_column("ROE", justify="right")
    t2.add_column("Margen Bruto", justify="right")
    t2.add_column("Margen Op.", justify="right")
    t2.add_column("FCF", justify="right")
    t2.add_column("D/E", justify="right")
    t2.add_column("Current Ratio", justify="right")
    t2.add_column("Insiders", justify="right", style="green")
    t2.add_column("Instituc.", justify="right", style="blue")
    t2.add_column("Moat", justify="center")

    for ticker, analyzer in items:
        s = analyzer.get_summary()
        metrics = analyzer.get_key_metrics()
        valuation = metrics.get("valuation", {})
        debt = metrics.get("debt", {})
        dividends = metrics.get("dividends", {})
        profitability = metrics.get("profitability", {})
        ownership = metrics.get("ownership", {})
        moat_info = metrics.get("moat", {})

        # Margen operativo del anio mas reciente
        margins_by_year = profitability.get("margins_by_year", {})
        latest_year = sorted(margins_by_year.keys(), reverse=True)[0] if margins_by_year else None
        op_margin = margins_by_year[latest_year]["operating_margin"] if latest_year else None

        ytd_val = calculate_ytd(ticker)

        t1.add_row(
            s["ticker"],
            s["name"],
            format_number(s.get("price"), prefix="$"),
            format_pct(ytd_val),
            format_number(s.get("market_cap"), prefix="$"),
            format_number(s.get("pe_trailing")),
            format_number(valuation.get("peg_ratio")),
            format_pct_raw(s.get("dividend_yield")),
            format_pct(dividends.get("payout_ratio")),
        )

        moat_badge = "N/A"
        if moat_info.get("has_thesis"):
            r = moat_info.get("rating", "")
            if r == "Wide":
                moat_badge = "[bold green]Wide[/bold green]"
            elif r == "Narrow":
                moat_badge = "[bold yellow]Narrow[/bold yellow]"
            elif r == "None":
                moat_badge = "[bold red]Sin Moat[/bold red]"

        t2.add_row(
            s["ticker"],
            format_pct(s.get("roe")),
            format_pct(s.get("gross_margin")),
            format_pct(op_margin),
            format_number(s.get("free_cash_flow"), prefix="$"),
            format_number(debt.get("debt_to_equity")),
            format_number(debt.get("current_ratio")),
            format_pct(ownership.get("held_percent_insiders")),
            format_pct(ownership.get("held_percent_institutions")),
            moat_badge,
        )

    console.print(t1)
    console.print()
    console.print(t2)


def show_moat_summary_table(items):
    """Muestra tabla comparativa especializada en Estructura de Inversores y Calificacion de Moat."""
    table = Table(title="Analisis Cualitativo de Moat & Estructura Accionaria", show_lines=True)
    table.add_column("Ticker", style="cyan", justify="center")
    table.add_column("Nombre", style="white", max_width=22)
    table.add_column("Insiders\n(Skin in Game)", justify="right", style="green")
    table.add_column("Instituciones\n(Smart Money)", justify="right", style="blue")
    table.add_column("Calificacion Moat", justify="center")
    table.add_column("Tendencia", justify="center")
    table.add_column("Fuentes de Ventaja Competitiva", style="dim", max_width=40)

    for ticker, analyzer in items:
        s = analyzer.get_summary()
        metrics = analyzer.get_key_metrics()
        ownership = metrics.get("ownership", {})
        moat = metrics.get("moat", {})

        if not moat.get("has_thesis"):
            continue

        rating_badge = MoatManager.get_rating_badge(moat.get("rating"))
        trend_badge = MoatManager.get_trend_badge(moat.get("trend"))
        sources = moat.get("sources", [])
        sources_str = ", ".join([MoatManager.get_source_label(k).split(" (")[0] for k in sources])

        table.add_row(
            s["ticker"],
            s["name"],
            format_pct(ownership.get("held_percent_insiders")),
            format_pct(ownership.get("held_percent_institutions")),
            rating_badge,
            trend_badge,
            sources_str or "N/A",
        )

    console.print(table)


def show_moat_detail(analyzer):
    """Muestra un panel detallado con la tesis cualitativa y fuentes de ventaja competitiva."""
    ticker = analyzer.ticker
    s = analyzer.get_summary()
    metrics = analyzer.get_key_metrics()
    ownership = metrics.get("ownership", {})
    moat = metrics.get("moat", {})

    rating = moat.get("rating", "None")
    trend = moat.get("trend", "Stable")
    sources = moat.get("sources", [])
    thesis = moat.get("thesis", "Pendiente de documentacion cualitativa.")
    threats = moat.get("threats", "Pendiente de analisis de riesgos de disrupcion.")

    rating_badge = MoatManager.get_rating_badge(rating)
    trend_badge = MoatManager.get_trend_badge(trend)

    sources_formatted = "\n".join([
        f"  [bold cyan]*[/bold cyan] {MoatManager.get_source_label(src)}"
        for src in sources
    ]) if sources else "  [dim]Sin fuentes especificadas[/dim]"

    insiders_pct = format_pct(ownership.get("held_percent_insiders"))
    inst_pct = format_pct(ownership.get("held_percent_institutions"))

    content = f"""[bold yellow]EMPRESA:[/bold yellow] [white]{s.get('name')}[/white] ({ticker}) | Sector: [dim]{s.get('sector')}[/dim]
[bold yellow]PRECIO:[/bold yellow] ${s.get('price', 0):.2f}  |  [bold yellow]CAPITALIZACION:[/bold yellow] {format_number(s.get('market_cap'), prefix='$')}

[bold magenta]1. ESTRUCTURA DE INVERSORES (Alineacion & Smart Money):[/bold magenta]
  * Directivos / Insiders ([italic]Skin in the Game[/italic]): [bold green]{insiders_pct}[/bold green]
  * Fondos e Institucionales ([italic]Smart Money[/italic]):   [bold blue]{inst_pct}[/bold blue]

[bold magenta]2. EVALUACION DEL FOSO ECONOMICO (MOAT):[/bold magenta]
  * Calificacion: [bold]{rating_badge}[/bold]
  * Tendencia:    [bold]{trend_badge}[/bold]

[bold magenta]3. FUENTES ACTIVAS DE VENTAJA COMPETITIVA:[/bold magenta]
{sources_formatted}

[bold green]4. TESIS CUALITATIVA DEL INVERSOR:[/bold green]
{thesis}

[bold red]5. PRINCIPALES AMENAZAS AL FOSO (Riesgos de Disrupcion):[/bold red]
{threats}
"""
    console.print(Panel(content, title=f"[bold]Foso Economico & Perspectiva de Inversores: {ticker}[/bold]", border_style="cyan"))
    console.print()


def show_reit_table(items):
    """Muestra tabla resumen para REITs."""
    table = Table(title="REITs", show_lines=True)
    table.add_column("Ticker", style="cyan", justify="center")
    table.add_column("Nombre", style="white", max_width=18)
    table.add_column("Precio", style="green", justify="right")
    table.add_column("YTD", justify="right")
    table.add_column("Div Yield", justify="right")
    table.add_column("FFO (ultimo)", justify="right")
    table.add_column("FFO Payout", justify="right")
    table.add_column("P/B", justify="right")
    table.add_column("D/E", justify="right")

    for ticker, analyzer in items:
        s = analyzer.get_summary()
        metrics = analyzer.get_key_metrics()

        ffo_data = metrics.get("ffo_analysis", {})
        latest_year = sorted(ffo_data.keys(), reverse=True)[0] if ffo_data else None
        ffo_payout = ffo_data[latest_year]["ffo_payout_ratio"] if latest_year else None

        ytd_val = calculate_ytd(ticker)

        table.add_row(
            s["ticker"],
            s["name"],
            format_number(s.get("price"), prefix="$"),
            format_pct(ytd_val),
            format_pct_raw(s.get("dividend_yield")),
            format_number(s.get("latest_ffo"), prefix="$"),
            format_pct(ffo_payout),
            format_number(s.get("price_to_book")),
            format_number(s.get("debt_to_equity")),
        )

    console.print(table)


def show_equity_etf_table(items):
    """Muestra tabla resumen para ETFs de renta variable."""
    table = Table(title="ETFs de Renta Variable", show_lines=True)
    table.add_column("Ticker", style="cyan", justify="center")
    table.add_column("Categoria", style="dim", max_width=16)
    table.add_column("Precio", style="green", justify="right")
    table.add_column("Div Yield", justify="right")
    table.add_column("Expense Ratio", justify="right")
    table.add_column("AUM", justify="right")
    table.add_column("YTD Return", justify="right")
    table.add_column("Beta 3Y", justify="right")

    for ticker, analyzer in items:
        s = analyzer.get_summary()
        metrics = analyzer.get_key_metrics()

        table.add_row(
            s["ticker"],
            s.get("category") or "N/A",
            format_number(s.get("price"), prefix="$"),
            format_pct(s.get("dividend_yield")),
            format_pct(s.get("expense_ratio")),
            format_number(s.get("total_assets"), prefix="$"),
            format_pct_raw(s.get("ytd_return")),
            format_number(metrics.get("performance", {}).get("beta_3y")),
        )

    console.print(table)


def show_bond_etf_table(items):
    """Muestra tabla resumen para ETFs de renta fija."""
    table = Table(title="ETFs de Renta Fija (Bonos)", show_lines=True)
    table.add_column("Ticker", style="cyan", justify="center")
    table.add_column("Categoria", style="dim", max_width=16)
    table.add_column("Precio", style="green", justify="right")
    table.add_column("Yield", justify="right")
    table.add_column("Expense Ratio", justify="right")
    table.add_column("AUM", justify="right")
    table.add_column("YTD Return", justify="right")
    table.add_column("Beta 3Y", justify="right")

    for ticker, analyzer in items:
        s = analyzer.get_summary()
        metrics = analyzer.get_key_metrics()

        table.add_row(
            s["ticker"],
            s.get("category") or "N/A",
            format_number(s.get("price"), prefix="$"),
            format_pct(metrics.get("yield_analysis", {}).get("yield")),
            format_pct(s.get("expense_ratio")),
            format_number(s.get("total_assets"), prefix="$"),
            format_pct_raw(s.get("ytd_return")),
            format_number(metrics.get("risk", {}).get("beta")),
        )

    console.print(table)


# =============================================================================
# Orquestador principal
# =============================================================================

def run_analysis():
    parser = argparse.ArgumentParser(description="Fundamental Analysis Hub CLI")
    parser.add_argument("--ticker", type=str, default=None, help="Filtrar analisis por un ticker especifico")
    parser.add_argument("--moat", action="store_true", help="Mostrar analisis cualitativo detallado de Moat y Tesis")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold green]FUNDAMENTAL ANALYSIS HUB[/bold green]\n"
        "Resumen de metricas clave, perspectiva de inversores y foso economico",
        border_style="green"
    ))
    console.print()

    # 1. Cargar watchlist y downloader (para leer cache)
    watchlist_mgr = WatchlistManager()
    downloader = FinancialDataDownloader()
    watchlist = watchlist_mgr.get_watchlist()

    if not watchlist:
        console.print("[bold red]Watchlist vacia.[/bold red]")
        return

    # Filtrar por ticker si se indico en linea de comandos
    if args.ticker:
        target_ticker = args.ticker.strip().upper()
        watchlist = [item for item in watchlist if item["ticker"].upper() == target_ticker]
        if not watchlist:
            console.print(f"[bold yellow]El ticker {target_ticker} no se encuentra en la watchlist. Analizando directamente...[/bold yellow]")
            watchlist = [{"ticker": target_ticker, "type": "equity"}]

    # 2. Agrupar por tipo y crear analizadores
    groups = {"equity": [], "reit": [], "equity_etf": [], "bond_etf": []}

    for item in watchlist:
        ticker = item["ticker"]
        asset_type = item.get("type", "equity")

        # Leer datos de la cache local
        data = downloader.get_cached_fundamentals(ticker)
        if data is None:
            console.print(f"[yellow]Sin datos en cache para {ticker}. Ejecuta main_data_update.py primero.[/yellow]")
            continue

        # Crear analizador via Factory
        try:
            analyzer = AnalyzerFactory.create(ticker, data, asset_type)
            groups.setdefault(asset_type, []).append((ticker, analyzer))
        except Exception as e:
            console.print(f"[red]Error creando analizador para {ticker}: {e}[/red]")

    # 3. Mostrar tablas por tipo
    if groups.get("equity"):
        show_equity_table(groups["equity"])
        console.print()

        # Si se activo --moat o se consulto un ticker especifico, mostrar seccion de Moat
        if args.moat or args.ticker:
            show_moat_summary_table(groups["equity"])
            console.print()
            for ticker, analyzer in groups["equity"]:
                metrics = analyzer.get_key_metrics()
                if metrics.get("moat", {}).get("has_thesis"):
                    show_moat_detail(analyzer)

    if groups.get("reit"):
        show_reit_table(groups["reit"])
        console.print()

    if groups.get("equity_etf"):
        show_equity_etf_table(groups["equity_etf"])
        console.print()

    if groups.get("bond_etf"):
        show_bond_etf_table(groups["bond_etf"])
        console.print()

    console.print("[bold green]Analisis completado.[/bold green]")


if __name__ == "__main__":
    run_analysis()
