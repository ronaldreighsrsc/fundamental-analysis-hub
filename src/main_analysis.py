import sys
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Asegurar que el modulo src sea importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.watchlist_manager import WatchlistManager
from src.data.downloader import FinancialDataDownloader
from src.analysis.analyzer_factory import AnalyzerFactory

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
        # Filtrar datos para el anio en curso (2026)
        df_year = df[df["Date"].dt.year == current_year]
        
        if df_year.empty:
            # Si no hay datos de este anio, tomamos el mas reciente registrado en el archivo
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

    # --- Tabla 2: Rentabilidad y Salud ---
    t2 = Table(title="Acciones - Rentabilidad y Salud Financiera", show_lines=True)
    t2.add_column("Ticker", style="cyan", justify="center")
    t2.add_column("ROE", justify="right")
    t2.add_column("Margen Bruto", justify="right")
    t2.add_column("Margen Op.", justify="right")
    t2.add_column("FCF", justify="right")
    t2.add_column("D/E", justify="right")
    t2.add_column("Current Ratio", justify="right")

    for ticker, analyzer in items:
        s = analyzer.get_summary()
        metrics = analyzer.get_key_metrics()
        valuation = metrics.get("valuation", {})
        debt = metrics.get("debt", {})
        dividends = metrics.get("dividends", {})
        profitability = metrics.get("profitability", {})

        # Obtener margen operativo del ultimo anio disponible
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

        t2.add_row(
            s["ticker"],
            format_pct(s.get("roe")),
            format_pct(s.get("gross_margin")),
            format_pct(op_margin),
            format_number(s.get("free_cash_flow"), prefix="$"),
            format_number(debt.get("debt_to_equity")),
            format_number(debt.get("current_ratio")),
        )

    console.print(t1)
    console.print()
    console.print(t2)


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

        # Obtener el payout del anio mas reciente
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
    console.print(Panel.fit(
        "[bold green]FUNDAMENTAL ANALYSIS HUB[/bold green]\n"
        "Resumen de metricas clave por tipo de activo",
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
