import sys
import os
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Asegurar que el modulo src sea importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.watchlist_manager import WatchlistManager
from src.data.downloader import FinancialDataDownloader

console = Console()

def run_update(force_download: bool = False):
    console.print("[bold green]=== PROCESO DE ACTUALIZACION DE DATOS FINANCIEROS ===[/bold green]\n")
    
    # 1. Cargar Watchlist
    try:
        watchlist_mgr = WatchlistManager()
        watchlist = watchlist_mgr.get_watchlist()
        tickers = watchlist_mgr.get_tickers()
        
        if not tickers:
            console.print("[bold red]La watchlist esta vacia. Agrega tickers a 'config/watchlist.json' primero.[/bold red]")
            return
            
        console.print(f"Cargados [bold cyan]{len(tickers)}[/bold cyan] activos para actualizar.\n")
    except Exception as e:
        console.print(f"[bold red]Error al cargar la watchlist: {e}[/bold red]")
        return

    # 2. Inicializar Downloader
    downloader = FinancialDataDownloader(cache_expiry_hours=24)
    
    # Tabla de resultados
    results_table = Table(title="Resumen de Descarga y Actualizacion")
    results_table.add_column("Ticker", style="cyan", justify="center")
    results_table.add_column("Nombre", style="white")
    results_table.add_column("Fundamentales", style="magenta", justify="center")
    results_table.add_column("Precios Historicos", style="magenta", justify="center")
    results_table.add_column("Detalles / Estado", style="green")

    # 3. Descargar datos con barra de progreso
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[yellow]Descargando datos...", total=len(watchlist))
        
        for item in watchlist:
            ticker = item["ticker"]
            name = item["name"]
            
            progress.update(task, description=f"[yellow]Procesando [bold]{ticker}[/bold]...")
            
            fund_status = "N/A"
            price_status = "N/A"
            detail = "OK"
            
            try:
                # Comprobar si ya existe cache valida
                paths = downloader._get_cache_paths(ticker)
                is_fund_cached = downloader._is_cache_valid(paths["fundamentals"])
                is_price_cached = downloader._is_cache_valid(paths["prices"])
                
                # Descargar fundamentales
                if not force_download and is_fund_cached:
                    fund_status = "[blue]Cached[/blue]"
                else:
                    downloader.fetch_fundamental_data(ticker, force=force_download)
                    fund_status = "[green]Updated[/green]"
                    
                # Descargar precios (historial de 5 años por defecto)
                if not force_download and is_price_cached:
                    price_status = "[blue]Cached[/blue]"
                else:
                    downloader.fetch_price_data(ticker, period="5y", force=force_download)
                    price_status = "[green]Updated[/green]"
                
                # Pausa para evitar rate limiting de Yahoo Finance si estamos descargando
                if "Updated" in fund_status or "Updated" in price_status:
                    time.sleep(1.5)
                    
            except Exception as e:
                detail = f"[red]Error: {str(e)}[/red]"
                if fund_status == "N/A":
                    fund_status = "[red]Error[/red]"
                if price_status == "N/A":
                    price_status = "[red]Error[/red]"
                    
            results_table.add_row(ticker, name, fund_status, price_status, detail)
            progress.advance(task)

    console.print("\n")
    console.print(results_table)
    console.print("\n[bold green]Proceso completado. Los datos locales estan listos para el analisis.[/bold green]")

if __name__ == "__main__":
    # Permite forzar la descarga de internet pasando el flag --force
    force = "--force" in sys.argv
    run_update(force_download=force)
