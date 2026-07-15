import yfinance as yf
from rich.console import Console
from rich.table import Table

console = Console()

def verify():
    console.print("[bold green]=== Verificando el entorno de Fundamental Analysis Hub ===[/bold green]\n")
    
    ticker_symbol = "AAPL"
    console.print(f"Obteniendo informacion basica de [bold blue]{ticker_symbol}[/bold blue] usando yfinance...")
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        table = Table(title=f"Datos de {info.get('longName', ticker_symbol)}")
        table.add_column("Metrica", style="cyan")
        table.add_column("Valor", style="magenta")
        
        table.add_row("Simbolo", info.get("symbol"))
        table.add_row("Sector", info.get("sector"))
        table.add_row("Precio Actual", f"${info.get('currentPrice', 'N/A')}")
        table.add_row("Capitalizacion de Mercado", f"${info.get('marketCap', 0):,}")
        table.add_row("P/E Ratio (Trailing)", str(info.get("trailingPE", "N/A")))
        
        console.print(table)
        console.print("\n[bold green]¡Todo funciona perfectamente![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Ocurrio un error al obtener datos: {e}[/bold red]")

if __name__ == "__main__":
    verify()
