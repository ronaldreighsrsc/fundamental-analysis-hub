import sys
import os
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Asegurar que el modulo src sea importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.analysis.research_report_generator import ResearchReportGenerator
from src.data.watchlist_manager import WatchlistManager

console = Console()


def run():
    parser = argparse.ArgumentParser(
        description="Generador de Reportes de Cobertura y Tesis de Inversión (Equity Research Initiating Coverage)"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Símbolo del activo a analizar (ej. AAPL, KO, DVA, MSFT)",
    )
    parser.add_argument(
        "--all-watchlist",
        action="store_true",
        help="Genera reportes de cobertura para todos los activos de renta variable en la watchlist",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Abre el reporte generado automáticamente en el editor predeterminado",
    )

    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold green]INSTITUTIONAL EQUITY RESEARCH ENGINE[/bold green]\n"
            "Generador de Tesis de Inversión, Auditoría de Solvencia y Consenso de Valuación (3 Pilares)",
            border_style="green",
        )
    )

    generator = ResearchReportGenerator()
    tickers = []

    if args.ticker:
        tickers.append(args.ticker.strip().upper())
    elif args.all_watchlist:
        wl = WatchlistManager().get_watchlist()
        tickers = [item["ticker"] for item in wl if item.get("type", "equity") == "equity"]
    else:
        # Por defecto si no se especifico nada, analizar AAPL
        tickers = ["AAPL"]

    for ticker in tickers:
        with console.status(f"[yellow]Analizando los 3 pilares y generando reporte para {ticker}...[/yellow]"):
            try:
                data = generator.generate_report_data(ticker)
                report_path = generator.export_report_to_file(ticker)
            except Exception as e:
                console.print(f"[bold red]Error generando reporte para {ticker}: {e}[/bold red]")
                continue

        consensus = data["consensus"]
        moat = data["moat"]
        solvency = data["solvency"]
        rec = consensus["recommendation"]

        rec_style = "bold green" if rec == "BUY" else ("bold yellow" if rec == "HOLD" else "bold red")

        # Tabla resumen ejecutivo en terminal
        table = Table(title=f"Resumen de Cobertura Institucional: {ticker} ({data['company_name']})", show_lines=True)
        table.add_column("Dimensión de Análisis", style="cyan")
        table.add_column("Métrica / Veredicto", justify="right")
        table.add_column("Detalle Metodológico", style="dim")

        table.add_row(
            "Recomendación Formal",
            f"[{rec_style}]{rec}[/{rec_style}]",
            "Consenso multi-modelo fundamental",
        )
        table.add_row(
            "Precio Actual",
            f"${consensus['current_price'] or 0.0:.2f}",
            "Último cierre de mercado",
        )
        table.add_row(
            "Valor Justo (Fair Value)",
            f"${consensus['fair_value'] or 0.0:.2f}",
            f"Promedio ponderado ({len(consensus['models_used'])} modelos)",
        )
        mos = consensus['margin_of_safety_pct']
        mos_str = f"{mos:+.1f}%" if mos is not None else "N/A"
        table.add_row(
            "Margen de Seguridad",
            f"[{rec_style}]{mos_str}[/{rec_style}]",
            "Descuento / Prima sobre valor intrínseco",
        )
        table.add_row(
            "Foso Económico (Moat)",
            f"{moat.get('rating', 'N/A')}",
            f"Tendencia: {moat.get('trend', 'N/A')}",
        )
        cr = f"{solvency.get('current_ratio'):.2f}x" if solvency.get('current_ratio') else "N/A"
        table.add_row(
            "Escudo de Solvencia (Current Ratio)",
            cr,
            "Liquidez corriente para pasivos a corto plazo",
        )

        console.print(table)
        console.print(f"[bold green]Reporte completo guardado en:[/bold green] [cyan]{report_path}[/cyan]\n")

        if args.open:
            try:
                os.startfile(report_path)
            except Exception:
                pass


if __name__ == "__main__":
    run()
