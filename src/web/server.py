import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Optional, Dict, Any

# Asegurar que la raiz del proyecto este en el PATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.portfolio.portfolio_manager import PortfolioManager
from src.portfolio.portfolio_analytics import PortfolioAnalytics
from src.data.watchlist_manager import WatchlistManager

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class PortfolioWebHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP que sirve la interfaz web estatica y responde a la API REST del portafolio."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    @property
    def manager(self) -> PortfolioManager:
        if not hasattr(self.server, "portfolio_manager"):
            self.server.portfolio_manager = PortfolioManager()
        return self.server.portfolio_manager

    @property
    def analytics(self) -> PortfolioAnalytics:
        return PortfolioAnalytics(self.manager)

    @property
    def watchlist_mgr(self) -> WatchlistManager:
        if not hasattr(self.server, "watchlist_manager"):
            self.server.watchlist_manager = WatchlistManager()
        return self.server.watchlist_manager

    def _send_json(self, data: Any, status: int = 200):
        """Helper para responder en formato JSON."""
        response_body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response_body)

    def _read_json_body(self) -> Dict[str, Any]:
        """Lee y parsea el cuerpo de una peticion POST."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(body) if body else {}

    def do_OPTIONS(self):
        """Manejo de pre-flight CORS."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Maneja peticiones GET para la API o archivos estaticos."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/portfolio":
            summary = self.manager.get_summary()
            positions = self.manager.get_positions()
            allocation = self.analytics.get_asset_allocation()
            sectors = self.analytics.get_sector_distribution()
            concentration = self.analytics.get_concentration_metrics()
            self._send_json({
                "summary": summary,
                "positions": positions,
                "allocation": allocation,
                "sectors": sectors,
                "concentration": concentration,
            })
            return

        elif path == "/api/timeline":
            benchmark = query.get("benchmark", ["SPY"])[0]
            timeline_data = self.analytics.get_benchmark_comparison(benchmark_ticker=benchmark)
            self._send_json(timeline_data)
            return

        elif path == "/api/quote":
            ticker = query.get("ticker", [""])[0].strip().upper()
            if not ticker:
                self._send_json({"error": "Ticker requerido"}, status=400)
                return
            price = self.manager.get_current_market_price(ticker)
            meta = self.manager.get_asset_metadata(ticker)
            self._send_json({
                "ticker": ticker,
                "price": round(price, 2) if price > 0 else None,
                "name": meta.get("name", ticker),
                "sector": meta.get("sector", "General"),
                "type": meta.get("type", "equity"),
            })
            return

        elif path == "/api/history":
            txs = self.manager.get_transaction_history()
            self._send_json({"transactions": txs})
            return

        elif path == "/api/watchlist":
            watchlist = self.watchlist_mgr.get_watchlist()
            self._send_json({"watchlist": watchlist})
            return

        elif path == "/api/export-csv":
            csv_path = self.manager.export_csv()
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="portfolio_transactions.csv"')
            self.send_header("Content-Length", str(len(content.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return

        # Servir archivos estaticos por defecto (index.html, style.css, app.js)
        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        """Maneja peticiones POST para ejecutar operaciones bursatiles y transacciones."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            body = self._read_json_body()
        except Exception as e:
            self._send_json({"error": f"JSON invalido: {e}"}, status=400)
            return

        try:
            if path == "/api/buy":
                ticker = body.get("ticker", "").strip().upper()
                shares = float(body.get("shares", 0))
                price = float(body.get("price")) if body.get("price") is not None else None
                fee = float(body.get("fee", 0.0))
                notes = body.get("notes", "Compra desde Web Trading Desk")

                tx = self.manager.buy(ticker=ticker, shares=shares, price=price, fee=fee, notes=notes)
                self._send_json({"success": True, "transaction": tx})
                return

            elif path == "/api/sell":
                ticker = body.get("ticker", "").strip().upper()
                shares = float(body.get("shares", 0))
                price = float(body.get("price")) if body.get("price") is not None else None
                fee = float(body.get("fee", 0.0))
                notes = body.get("notes", "Venta desde Web Trading Desk")

                tx = self.manager.sell(ticker=ticker, shares=shares, price=price, fee=fee, notes=notes)
                self._send_json({"success": True, "transaction": tx})
                return

            elif path == "/api/deposit":
                amount = float(body.get("amount", 0))
                notes = body.get("notes", "Aporte de capital web")
                tx = self.manager.deposit(amount=amount, notes=notes)
                self._send_json({"success": True, "transaction": tx})
                return

            elif path == "/api/simulate-monthly":
                amount = float(body.get("amount", 500.0))
                months = int(body.get("months", 6))
                notes = body.get("notes", "Aporte mensual sistematico DCA")
                txs = self.manager.simulate_monthly_deposits(monthly_amount=amount, months=months, notes=notes)
                self._send_json({"success": True, "created_count": len(txs)})
                return

            elif path == "/api/withdraw":
                amount = float(body.get("amount", 0))
                notes = body.get("notes", "Retiro de capital web")
                tx = self.manager.withdraw(amount=amount, notes=notes)
                self._send_json({"success": True, "transaction": tx})
                return

            elif path == "/api/dividend":
                ticker = body.get("ticker", "").strip().upper()
                amount = float(body.get("amount", 0))
                notes = body.get("notes", "Dividendo cobrado web")
                tx = self.manager.record_dividend(ticker=ticker, amount=amount, notes=notes)
                self._send_json({"success": True, "transaction": tx})
                return

            elif path == "/api/reset":
                initial_cash = float(body.get("initial_cash", 100_000.0))
                self.manager.reset_portfolio(initial_cash=initial_cash)
                self._send_json({"success": True, "initial_cash": initial_cash})
                return

            else:
                self._send_json({"error": f"Endpoint no encontrado: {path}"}, status=404)
                return

        except ValueError as ve:
            self._send_json({"error": str(ve)}, status=400)
        except Exception as ex:
            self._send_json({"error": f"Error interno: {ex}"}, status=500)


def create_server(host: str = "127.0.0.1", port: int = 5000, manager: Optional[PortfolioManager] = None) -> ThreadingHTTPServer:
    """Crea y configura la instancia del servidor HTTP."""
    server = ThreadingHTTPServer((host, port), PortfolioWebHandler)
    if manager is not None:
        server.portfolio_manager = manager
    return server


def run_server(host: str = "127.0.0.1", port: int = 5000, open_browser: bool = True):
    """Inicia el servidor web en bucle continuo."""
    import webbrowser

    server = create_server(host, port)
    url = f"http://{host}:{port}"
    print(f"\n[+] Servidor Web Broker & Trading Terminal activo en: {url}")
    print("[+] Presiona Ctrl+C para detener el servidor.\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Deteniendo servidor...")
    finally:
        server.server_close()
        print("[+] Servidor detenido correctamente.")


if __name__ == "__main__":
    run_server()
