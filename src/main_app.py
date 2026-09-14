import os
import sys
import socket
from rich.console import Console
from rich.panel import Panel

# Configurar encoding UTF-8 en Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar importacion de src
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.web.server import run_server

console = Console()


def find_available_port(start_port: int = 5000, max_attempts: int = 20) -> int:
    """Busca un puerto libre a partir de start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


def main():
    host = "127.0.0.1"
    port = find_available_port(5000)
    url = f"http://{host}:{port}"

    banner_text = f"""[bold cyan]FUNDAMENTAL ANALYSIS HUB[/bold cyan]
[bold white]Institutional Broker & Trading Terminal (Web App)[/bold white]

[green]● Servidor local iniciado correctamente.[/green]
[white]URL de Acceso:[/white] [bold underline cyan]{url}[/bold underline cyan]

[dim]* Panel de órdenes en tiempo real (Comprar, Vender, DCA $500/mes)
* Cotizaciones en vivo e historial de auditoría
* Gráfico interactivo: Valor Cartera vs Aportes vs S&P 500 (SPY)
* Presiona [bold red]Ctrl+C[/bold red] en cualquier momento para detener el servidor.[/dim]
"""

    console.print(
        Panel(banner_text, title="[bold green]WEB TRADING DESK ONLINE[/bold green]", border_style="cyan")
    )

    run_server(host=host, port=port, open_browser=True)


if __name__ == "__main__":
    main()
