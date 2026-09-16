import sys
import os
import argparse
from rich.console import Console
from rich.table import Table
from rich import box

# Asegurar que el modulo src sea importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.portfolio.portfolio_manager import PortfolioManager
from src.visualization.portfolio_charts import (
    render_terminal_portfolio,
    create_portfolio_dashboard,
)

console = Console()


def run():
    parser = argparse.ArgumentParser(
        description="Simulador de Inversiones y Auditor de Portafolio (Paper Trading & Audit Engine)"
    )

    # Acciones de trading
    parser.add_argument("--buy", type=str, default=None, help="Comprar acciones de un ticker (ej. --buy DVA --shares 25)")
    parser.add_argument("--sell", type=str, default=None, help="Vender acciones de un ticker (ej. --sell AAPL --shares 10)")
    parser.add_argument("--shares", type=float, default=None, help="Cantidad de acciones a operar")
    parser.add_argument("--price", type=float, default=None, help="Precio de ejecucion por accion (opcional, por defecto precio actual)")
    parser.add_argument("--fee", type=float, default=0.0, help="Comision de corretaje (por defecto $0.0)")
    parser.add_argument("--notes", type=str, default="", help="Nota o tesis de inversion para la operacion")

    # Gestion de efectivo
    parser.add_argument("--deposit", type=float, default=None, help="Depositar efectivo en la cuenta (ej. --deposit 10000)")
    parser.add_argument("--withdraw", type=float, default=None, help="Retirar efectivo de la cuenta")
    parser.add_argument("--dividend", type=float, default=None, help="Registrar cobro de dividendo en efectivo")
    parser.add_argument("--ticker", type=str, default=None, help="Ticker asociado al dividendo")

    # Vistas y utilidades
    parser.add_argument("--history", action="store_true", help="Mostrar libro contable completo de transacciones")
    parser.add_argument("--plot", action="store_true", help="Generar y abrir dashboard interactivo Plotly en el navegador")
    parser.add_argument("--benchmark", type=str, default="SPY", help="Benchmark de comparacion (por defecto SPY / S&P 500)")
    parser.add_argument("--simulate-monthly", type=float, default=None, help="Simular serie historica de aportes mensuales recurrentes (ej. --simulate-monthly 500 --months 6)")
    parser.add_argument("--months", type=int, default=1, help="Cantidad de meses para la simulacion de aportes recurrentes (por defecto 1)")
    parser.add_argument("--start-date", type=str, default="2026-10-01", help="Fecha de inicio para aportes (por defecto 2026-10-01)")
    parser.add_argument("--day", type=int, default=1, help="Dia del mes para cada aporte mensual (por defecto 1)")
    parser.add_argument("--reset", action="store_true", help="Reiniciar portafolio con $100.000 USD de capital simulado")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Monto para reiniciar el portafolio (usar con --reset)")
    parser.add_argument("--backup", action="store_true", help="Crear respaldo JSON portable del portafolio en exports/backups/")
    parser.add_argument("--restore", type=str, default=None, help="Restaurar portafolio desde archivo JSON de respaldo")
    parser.add_argument("--export-csv", action="store_true", help="Exportar todas las transacciones auditadas a formato CSV")
    parser.add_argument("--sync-actions", action="store_true", help="Sincronizar y cobrar automaticamente dividendos y desdoblamientos (splits)")
    parser.add_argument("--dividend-calendar", action="store_true", help="Mostrar calendario proyectado de dividendos y metricas de Yield on Cost")
    parser.add_argument("--split", type=float, default=None, help="Registrar un desdoblamiento de acciones manual (ej. --split 10 --ticker NVDA)")



    args = parser.parse_args()
    manager = PortfolioManager()

    # 1. Respaldo y Restauracion
    if args.backup:
        try:
            saved_path = manager.export_backup()
            console.print(f"[bold green]Respaldo exportado exitosamente a:[/bold green]\n[cyan]{saved_path}[/cyan]\n")
            return
        except Exception as e:
            console.print(f"[bold red]Error al crear respaldo: {e}[/bold red]\n")
            return

    if args.restore:
        try:
            res = manager.import_backup(args.restore)
            console.print(
                f"[bold green]Portafolio restaurado exitosamente desde:[/bold green] [cyan]{args.restore}[/cyan]\n"
                f"[white]Transacciones cargadas: {res['transactions_count']} | Capital inicial: ${res['initial_cash']:,.2f}[/white]\n"
            )
            render_terminal_portfolio(manager)
            return
        except Exception as e:
            console.print(f"[bold red]Error al restaurar respaldo: {e}[/bold red]\n")
            return

    if args.export_csv:
        try:
            csv_path = manager.export_csv()
            console.print(f"[bold green]Historial de transacciones exportado a CSV:[/bold green]\n[cyan]{csv_path}[/cyan]\n")
            return
        except Exception as e:
            console.print(f"[bold red]Error al exportar CSV: {e}[/bold red]\n")
            return

    # Sincronizacion de eventos corporativos (Splits y Dividendos)
    if args.sync_actions:
        try:
            with console.status("[bold cyan]Sincronizando eventos corporativos oficiales (Splits & Dividendos)...[/bold cyan]"):
                res = manager.sync_corporate_actions()
            splits = res.get("applied_splits", [])
            divs = res.get("applied_dividends", [])
            total_credited = res.get("total_dividends_credited", 0.0)

            console.print("\n[bold green]=== SINCRONIZACIÓN DE ACCIONES CORPORATIVAS COMPLETADA ===[/bold green]")
            if splits:
                console.print(f"[bold cyan]Splits aplicados ({len(splits)}):[/bold cyan]")
                for s in splits:
                    console.print(f"  • [yellow]{s['ticker']}[/yellow]: Split {s['ratio']:g}:1 el {s['date']} ({s['shares_before']:g} -> {s['shares_after']:g} accs)")
            else:
                console.print("[dim]No se detectaron nuevos splits pendientes.[/dim]")

            if divs:
                console.print(f"\n[bold cyan]Dividendos acreditados en caja ({len(divs)}):[/bold cyan]")
                for d in divs:
                    console.print(f"  • [yellow]{d['ticker']}[/yellow]: ${d['dps']:.4f}/acc el {d['date']} ({d['shares']} accs) -> [green]+${d['total']:,.2f} USD[/green]")
                console.print(f"\n[bold green]Total efectivo acreditado: +${total_credited:,.2f} USD[/bold green]\n")
            else:
                console.print("[dim]No se detectaron dividendos pendientes por cobrar.[/dim]\n")
        except Exception as e:
            console.print(f"[bold red]Error al sincronizar eventos corporativos: {e}[/bold red]\n")
        render_terminal_portfolio(manager)
        return

    # Calendario y proyeccion de dividendos
    if args.dividend_calendar:
        try:
            with console.status("[bold cyan]Calculando proyeccion de dividendos y Yield on Cost...[/bold cyan]"):
                cal_data = manager.get_dividend_calendar()
            table = Table(title="Calendario y Proyeccion de Dividendos", box=box.ROUNDED)
            table.add_column("Ticker", style="bold yellow")
            table.add_column("Acciones", justify="right")
            table.add_column("DPS Anual ($)", justify="right")
            table.add_column("Ingreso Anual ($)", justify="right", style="green")
            table.add_column("Div Yield", justify="right")
            table.add_column("Yield on Cost (YoC)", justify="right", style="bold cyan")
            table.add_column("Prox Ex-Date", justify="center")
            table.add_column("Prox Pay Date", justify="center")

            for h in cal_data.get("holdings", []):
                table.add_row(
                    h["ticker"],
                    f"{h['shares']:g}",
                    f"${h['dps']:,.2f}",
                    f"${h['annual_income']:,.2f}",
                    f"{h['dividend_yield_pct']:.2f}%",
                    f"{h['yield_on_cost_pct']:.2f}%",
                    h["ex_dividend_date"],
                    h["pay_date"],
                )
            console.print(table)
            console.print(f"\n[bold green]Ingreso Total Anual Estimado:[/bold green] ${cal_data['portfolio_annual_income']:,.2f} USD")
            console.print(f"[bold cyan]Dividend Yield Ponderado de Cartera:[/bold cyan] {cal_data['portfolio_dividend_yield_pct']:.2f}%\n")
        except Exception as e:
            console.print(f"[bold red]Error al obtener calendario de dividendos: {e}[/bold red]\n")
        return

    # Registro manual de Split
    if args.split is not None:
        if not args.ticker:
            console.print("[bold red]Debes especificar --ticker para aplicar el split (ej. --split 4 --ticker AAPL).[/bold red]")
            return
        try:
            tx = manager.record_split(ticker=args.ticker, ratio=args.split, notes=args.notes or None)
            console.print(f"[bold green]Split {args.split:g}:1 registrado exitosamente para {args.ticker}.[/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Error al registrar split: {e}[/bold red]\n")
            return

    # 2. Reinicio de portafolio
    if args.reset:
        confirm = True
        if confirm:
            manager.reset_portfolio(initial_cash=args.initial_cash)
            console.print(
                f"[bold green]Portafolio reiniciado exitosamente con ${args.initial_cash:,.2f} USD de capital simulado.[/bold green]\n"
            )
            render_terminal_portfolio(manager)
            return

    # 3. Depositos y retiros
    if args.deposit is not None:
        try:
            tx = manager.deposit(args.deposit, notes=args.notes or "Aporte de capital simulado")
            console.print(f"[bold green]Deposito de ${args.deposit:,.2f} USD registrado con exito.[/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Error en deposito: {e}[/bold red]\n")
            return

    if args.withdraw is not None:
        try:
            tx = manager.withdraw(args.withdraw, notes=args.notes or "Retiro de capital")
            console.print(f"[bold green]Retiro de ${args.withdraw:,.2f} USD registrado con exito.[/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Error en retiro: {e}[/bold red]\n")
            return

    if args.simulate_monthly is not None:
        try:
            created = manager.simulate_monthly_deposits(
                monthly_amount=args.simulate_monthly,
                months=args.months,
                start_date=args.start_date,
                day_of_month=args.day,
                notes=args.notes or "Aporte mensual DCA",
            )
            console.print(
                f"[bold green]Simulacion completada: {len(created)} aportes mensuales de ${args.simulate_monthly:,.2f} USD "
                f"(iniciando {args.start_date} dia {args.day}) registrados.[/bold green]\n"
            )
        except Exception as e:
            console.print(f"[bold red]Error en simulacion de aportes: {e}[/bold red]\n")
            return

    # 4. Dividendos
    if args.dividend is not None:
        if not args.ticker:
            console.print("[bold red]Debes especificar --ticker para asociar el dividendo (ej. --dividend 150 --ticker O).[/bold red]")
            return
        try:
            tx = manager.record_dividend(args.ticker, args.dividend, notes=args.notes or "Dividendo recibido")
            console.print(f"[bold green]Dividendo de ${args.dividend:,.2f} USD para {args.ticker} registrado.[/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Error en registro de dividendo: {e}[/bold red]\n")
            return

    # 5. Compras
    if args.buy is not None:
        if args.shares is None or args.shares <= 0:
            console.print("[bold red]Debes especificar la cantidad de acciones con --shares (ej. --buy DVA --shares 25).[/bold red]")
            return
        try:
            with console.status(f"[yellow]Ejecutando orden de compra para {args.buy.upper()}...[/yellow]"):
                tx = manager.buy(
                    ticker=args.buy,
                    shares=args.shares,
                    price=args.price,
                    fee=args.fee,
                    notes=args.notes or "Compra simulada de mercado",
                )
            console.print(
                f"[bold green]COMPRA EJECUTADA:[/bold green] {tx['shares']} de {tx['ticker']} "
                f"a ${tx['price']:,.2f} USD (Total: ${tx['total']:,.2f} USD)\n"
            )
        except Exception as e:
            console.print(f"[bold red]Error en compra: {e}[/bold red]\n")
            return

    # 6. Ventas
    if args.sell is not None:
        if args.shares is None or args.shares <= 0:
            console.print("[bold red]Debes especificar la cantidad de acciones con --shares (ej. --sell AAPL --shares 10).[/bold red]")
            return
        try:
            with console.status(f"[yellow]Ejecutando orden de venta para {args.sell.upper()}...[/yellow]"):
                tx = manager.sell(
                    ticker=args.sell,
                    shares=args.shares,
                    price=args.price,
                    fee=args.fee,
                    notes=args.notes or "Venta simulada de mercado",
                )
            console.print(
                f"[bold green]VENTA EJECUTADA:[/bold green] {tx['shares']} de {tx['ticker']} "
                f"a ${tx['price']:,.2f} USD (Total acreditado: ${tx['total']:,.2f} USD)\n"
            )
        except Exception as e:
            console.print(f"[bold red]Error en venta: {e}[/bold red]\n")
            return

    # 7. Graficos
    if args.plot:
        with console.status("[yellow]Generando dashboard interactivo Plotly con benchmark...[/yellow]"):
            path = create_portfolio_dashboard(manager, auto_open=True, benchmark_ticker=args.benchmark)
        console.print(f"[bold green]Dashboard de portafolio abierto en tu navegador.[/bold green]\n[dim]Archivo: {path}[/dim]\n")

    # Renderizar siempre el dashboard del portafolio en consola
    render_terminal_portfolio(manager)


if __name__ == "__main__":
    run()
