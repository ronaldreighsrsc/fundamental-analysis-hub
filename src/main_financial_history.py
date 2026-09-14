import sys
import os
import argparse
from rich.console import Console
from rich.panel import Panel

# Asegurar que el modulo src sea importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.visualization.financial_charts import (
    render_terminal_financial_table,
    create_financial_history_chart,
)

console = Console()


def run():
    parser = argparse.ArgumentParser(
        description="Extraccion de estados financieros historicos oficiales (10-K y 10-Q de la SEC EDGAR)"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="Simbolo del activo a analizar (ej. AAPL, DVA, KO, MSFT)",
    )
    parser.add_argument(
        "--period",
        type=str,
        choices=["annual", "quarterly"],
        default="annual",
        help="Periodo de los estados financieros: annual (10-K) o quarterly (10-Q)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=None,
        help="Numero maximo de anios recientes a visualizar (por defecto todos)",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Genera y abre un dashboard interactivo Plotly en tu navegador web",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fuerza la descarga directa desde la SEC ignorando la cache local",
    )

    args = parser.parse_args()
    ticker = args.ticker.strip().upper()

    console.print(
        Panel.fit(
            f"[bold green]SEC EDGAR FINANCIAL HISTORY[/bold green]\n"
            f"Extraccion oficial de informes { '10-K (Anuales)' if args.period == 'annual' else '10-Q (Trimestrales)' } para [bold cyan]{ticker}[/bold cyan]",
            border_style="green",
        )
    )

    extractor = SecFinancialExtractor()

    try:
        with console.status(f"[yellow]Consultando base de datos publica de la SEC para {ticker}...[/yellow]"):
            df = extractor.get_financial_history(ticker, period_type=args.period, force=args.force)
            company_name = extractor.get_company_name(ticker)

        if df.empty:
            console.print(f"[bold red]No se encontraron estados financieros archivados en la SEC para {ticker}.[/bold red]")
            return

        # Filtrar por cantidad de periodos si se especifico
        if args.years and args.years > 0:
            df = df.tail(args.years)

        # Mostrar tabla enriquecida en la terminal
        render_terminal_financial_table(ticker, df, company_name)

        # Si se solicito grafico interactivo
        if args.plot:
            with console.status("[yellow]Generando dashboard interactivo Plotly...[/yellow]"):
                chart_path = create_financial_history_chart(
                    ticker, df, company_name=company_name, auto_open=True
                )
            console.print(
                f"[bold green]Dashboard interactivo abierto en tu navegador.[/bold green]\n"
                f"[dim]Guardado en: {chart_path}[/dim]\n"
            )

    except Exception as e:
        console.print(f"[bold red]Error al procesar la informacion de la SEC: {e}[/bold red]")


if __name__ == "__main__":
    run()
