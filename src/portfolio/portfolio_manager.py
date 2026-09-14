import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import yfinance as yf

from src.data.downloader import FinancialDataDownloader
from src.data.watchlist_manager import WatchlistManager


class PortfolioManager:
    """
    Motor de gestion y simulacion de portafolio de inversiones (Paper Trading & Audit Engine).
    Utiliza el patron Event Sourcing: el estado actual del portafolio (caja, posiciones,
    costo promedio y ganancias realizadas) se reconstruye a partir de un libro contable
    inmutable de transacciones (transactions.json).
    """

    DEFAULT_INITIAL_CASH = 100_000.0

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.data_dir = os.path.join(base_dir, "data", "portfolio")
        else:
            self.data_dir = data_dir

        os.makedirs(self.data_dir, exist_ok=True)
        self.transactions_path = os.path.join(self.data_dir, "transactions.json")
        self.config_path = os.path.join(self.data_dir, "portfolio_config.json")

        self.downloader = FinancialDataDownloader()
        self.watchlist_mgr = WatchlistManager()

        self._ensure_initialized()

    def _ensure_initialized(self):
        """Inicializa la configuracion y el libro de transacciones si no existen."""
        if not os.path.exists(self.config_path):
            config = {
                "portfolio_name": "Paper Trading Portfolio",
                "base_currency": "USD",
                "created_at": datetime.now().isoformat(),
                "initial_cash": self.DEFAULT_INITIAL_CASH,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

        if not os.path.exists(self.transactions_path):
            # Deposito inicial por defecto
            initial_tx = [
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "type": "DEPOSIT",
                    "ticker": "CASH",
                    "shares": 1.0,
                    "price": self.DEFAULT_INITIAL_CASH,
                    "fee": 0.0,
                    "total": self.DEFAULT_INITIAL_CASH,
                    "notes": "Capital inicial para simulacion de inversiones",
                }
            ]
            with open(self.transactions_path, "w", encoding="utf-8") as f:
                json.dump(initial_tx, f, indent=2)

    def _load_transactions(self) -> List[Dict[str, Any]]:
        """Lee el libro contable de transacciones."""
        if not os.path.exists(self.transactions_path):
            return []
        try:
            with open(self.transactions_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_transactions(self, transactions: List[Dict[str, Any]]) -> bool:
        """Guarda el libro contable en disco."""
        try:
            with open(self.transactions_path, "w", encoding="utf-8") as f:
                json.dump(transactions, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def _load_config(self) -> Dict[str, Any]:
        """Lee la configuracion del portafolio."""
        if not os.path.exists(self.config_path):
            return {
                "portfolio_name": "Paper Trading Portfolio",
                "base_currency": "USD",
                "created_at": datetime.now().isoformat(),
                "initial_cash": self.DEFAULT_INITIAL_CASH,
            }
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"initial_cash": self.DEFAULT_INITIAL_CASH}

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Guarda la configuracion del portafolio en disco."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def reset_portfolio(self, initial_cash: float = 100_000.0) -> bool:
        """Reinicia el portafolio con un saldo de efectivo limpio."""
        config = {
            "portfolio_name": "Paper Trading Portfolio",
            "base_currency": "USD",
            "created_at": datetime.now().isoformat(),
            "initial_cash": float(initial_cash),
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        tx = [
            {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "type": "DEPOSIT",
                "ticker": "CASH",
                "shares": 1.0,
                "price": float(initial_cash),
                "fee": 0.0,
                "total": float(initial_cash),
                "notes": f"Reinicio de portafolio con ${initial_cash:,.2f} USD",
            }
        ]
        return self._save_transactions(tx)

    def get_current_market_price(self, ticker: str) -> float:
        """
        Obtiene el precio actual de mercado de un ticker desde la cache local
        o directamente desde yfinance.
        """
        ticker_clean = ticker.strip().upper()
        # 1. Intentar desde cache de fundamentales
        cached = self.downloader.get_cached_fundamentals(ticker_clean)
        if cached:
            info = cached.get("info", {})
            p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if p and float(p) > 0:
                return float(p)

        # 2. Intentar desde yfinance en vivo
        try:
            t = yf.Ticker(ticker_clean)
            fast_info = getattr(t, "fast_info", {})
            last_p = fast_info.get("lastPrice") or fast_info.get("previousClose")
            if last_p and float(last_p) > 0:
                return float(last_p)
            info = t.info
            p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if p and float(p) > 0:
                return float(p)
        except Exception:
            pass

        return 0.0

    def get_asset_metadata(self, ticker: str) -> Dict[str, str]:
        """Obtiene nombre, sector y tipo de activo para un ticker dado."""
        ticker_clean = ticker.strip().upper()
        watchlist = self.watchlist_mgr.get_watchlist()
        for item in watchlist:
            if item["ticker"].upper() == ticker_clean:
                return {
                    "name": item.get("name", ticker_clean),
                    "sector": item.get("sector", "General"),
                    "type": item.get("type", "equity"),
                }

        # Intentar desde cache de fundamentales
        cached = self.downloader.get_cached_fundamentals(ticker_clean)
        if cached:
            info = cached.get("info", {})
            return {
                "name": info.get("longName") or info.get("shortName") or ticker_clean,
                "sector": info.get("sector") or info.get("category") or "General",
                "type": "equity",
            }

        return {"name": ticker_clean, "sector": "General", "type": "equity"}

    def deposit(self, amount: float, notes: str = "Aporte de capital") -> Dict[str, Any]:
        """Deposita efectivo en el portafolio."""
        if amount <= 0:
            raise ValueError("El monto del deposito debe ser mayor a 0.")

        txs = self._load_transactions()
        tx = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": "DEPOSIT",
            "ticker": "CASH",
            "shares": 1.0,
            "price": float(amount),
            "fee": 0.0,
            "total": float(amount),
            "notes": notes,
        }
        txs.append(tx)
        self._save_transactions(txs)
        return tx

    def withdraw(self, amount: float, notes: str = "Retiro de capital") -> Dict[str, Any]:
        """Retira efectivo del portafolio si hay liquidez suficiente."""
        if amount <= 0:
            raise ValueError("El monto de retiro debe ser mayor a 0.")

        summary = self.get_summary()
        current_cash = summary["cash_balance"]
        if amount > current_cash:
            raise ValueError(
                f"Fondos insuficientes para retirar ${amount:,.2f}. Efectivo disponible: ${current_cash:,.2f}"
            )

        txs = self._load_transactions()
        tx = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": "WITHDRAW",
            "ticker": "CASH",
            "shares": 1.0,
            "price": float(amount),
            "fee": 0.0,
            "total": float(amount),
            "notes": notes,
        }
        txs.append(tx)
        self._save_transactions(txs)
        return tx

    def buy(
        self,
        ticker: str,
        shares: float,
        price: Optional[float] = None,
        fee: float = 0.0,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Ejecuta una orden de compra simulada.
        Calcula el impacto en caja y registra la operacion en el libro contable.
        """
        ticker_clean = ticker.strip().upper()
        if shares <= 0:
            raise ValueError("La cantidad de acciones debe ser mayor a 0.")

        # Resolver precio de ejecucion
        exec_price = price
        if exec_price is None or exec_price <= 0:
            exec_price = self.get_current_market_price(ticker_clean)

        if exec_price <= 0:
            raise ValueError(
                f"No se pudo determinar el precio de mercado para {ticker_clean}. "
                f"Por favor, especifica el precio manualmente con --price."
            )

        total_cost = (shares * exec_price) + fee
        summary = self.get_summary()
        current_cash = summary["cash_balance"]

        if total_cost > current_cash:
            raise ValueError(
                f"Liquidez insuficiente para comprar {shares} acciones de {ticker_clean}. "
                f"Costo total: ${total_cost:,.2f} USD | Efectivo disponible: ${current_cash:,.2f} USD"
            )

        txs = self._load_transactions()
        tx = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": "BUY",
            "ticker": ticker_clean,
            "shares": float(shares),
            "price": float(exec_price),
            "fee": float(fee),
            "total": float(total_cost),
            "notes": notes,
        }
        txs.append(tx)
        self._save_transactions(txs)
        return tx

    def sell(
        self,
        ticker: str,
        shares: float,
        price: Optional[float] = None,
        fee: float = 0.0,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Ejecuta una orden de venta simulada.
        Verifica que se posean suficientes titulos, acredita el efectivo y
        registra la ganancia/perdida realizada.
        """
        ticker_clean = ticker.strip().upper()
        if shares <= 0:
            raise ValueError("La cantidad de acciones a vender debe ser mayor a 0.")

        positions = self.get_positions()
        pos = positions.get(ticker_clean)

        if not pos or pos["shares"] < shares:
            owned = pos["shares"] if pos else 0.0
            raise ValueError(
                f"No posees suficientes acciones de {ticker_clean} para vender. "
                f"En posesion: {owned} | Intentando vender: {shares}"
            )

        # Resolver precio de ejecucion
        exec_price = price
        if exec_price is None or exec_price <= 0:
            exec_price = self.get_current_market_price(ticker_clean)

        if exec_price <= 0:
            raise ValueError(
                f"No se pudo determinar el precio de mercado para {ticker_clean}. "
                f"Por favor, especifica el precio manualmente con --price."
            )

        gross_proceeds = shares * exec_price
        net_proceeds = gross_proceeds - fee

        txs = self._load_transactions()
        tx = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": "SELL",
            "ticker": ticker_clean,
            "shares": float(shares),
            "price": float(exec_price),
            "fee": float(fee),
            "total": float(net_proceeds),
            "notes": notes,
        }
        txs.append(tx)
        self._save_transactions(txs)
        return tx

    def record_dividend(self, ticker: str, amount: float, notes: str = "Cobro de dividendos") -> Dict[str, Any]:
        """Registra el cobro de dividendos en efectivo generado por un activo."""
        ticker_clean = ticker.strip().upper()
        if amount <= 0:
            raise ValueError("El monto del dividendo debe ser mayor a 0.")

        txs = self._load_transactions()
        tx = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "type": "DIVIDEND",
            "ticker": ticker_clean,
            "shares": 0.0,
            "price": 0.0,
            "fee": 0.0,
            "total": float(amount),
            "notes": notes,
        }
        txs.append(tx)
        self._save_transactions(txs)
        return tx

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Reconstruye el estado actual de todas las posiciones abiertas re-procesando
        el historial de transacciones (Event Sourcing) con Base de Costo Promedio Ponderado.
        """
        txs = self._load_transactions()
        # ticker: {'shares': float, 'total_cost': float, 'fees': float}
        raw_positions: Dict[str, Dict[str, float]] = {}

        for tx in txs:
            t_type = tx["type"]
            ticker = tx["ticker"]
            shares = float(tx.get("shares", 0))
            price = float(tx.get("price", 0))
            fee = float(tx.get("fee", 0))

            if t_type == "BUY":
                if ticker not in raw_positions:
                    raw_positions[ticker] = {"shares": 0.0, "total_cost": 0.0}
                raw_positions[ticker]["shares"] += shares
                raw_positions[ticker]["total_cost"] += (shares * price) + fee

            elif t_type == "SELL":
                if ticker in raw_positions and raw_positions[ticker]["shares"] > 0:
                    current_shares = raw_positions[ticker]["shares"]
                    avg_cost = raw_positions[ticker]["total_cost"] / current_shares
                    # Reducir proporcionalmente el costo de la posicion
                    raw_positions[ticker]["shares"] -= shares
                    raw_positions[ticker]["total_cost"] -= (shares * avg_cost)
                    if raw_positions[ticker]["shares"] <= 0.000001:
                        del raw_positions[ticker]

        # Enriquecer posiciones con precios de mercado y metadatos
        positions = {}
        for ticker, data in raw_positions.items():
            shares = data["shares"]
            total_cost = data["total_cost"]
            avg_cost = total_cost / shares if shares > 0 else 0.0

            current_price = self.get_current_market_price(ticker)
            market_val = shares * current_price if current_price > 0 else total_cost
            unrealized_pnl = market_val - total_cost
            unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

            meta = self.get_asset_metadata(ticker)

            positions[ticker] = {
                "ticker": ticker,
                "name": meta.get("name", ticker),
                "sector": meta.get("sector", "General"),
                "type": meta.get("type", "equity"),
                "shares": round(shares, 4),
                "avg_cost": round(avg_cost, 2),
                "total_cost": round(total_cost, 2),
                "current_price": round(current_price, 2),
                "market_value": round(market_val, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                "weight_pct": 0.0,
            }

        # Calcular efectivo y peso relativo de cada posicion
        cash = 0.0
        for tx in txs:
            t_type = tx.get("type")
            tot = float(tx.get("total", 0))
            if t_type in ("DEPOSIT", "DIVIDEND", "SELL"):
                cash += tot
            elif t_type in ("WITHDRAW", "BUY"):
                cash -= tot

        total_nav = cash + sum(p["market_value"] for p in positions.values())
        if total_nav > 0:
            for p in positions.values():
                p["weight_pct"] = round((p["market_value"] / total_nav * 100), 2)

        return positions

    def get_summary(self) -> Dict[str, Any]:
        """
        Calcula el resumen ejecutivo del portafolio:
        - Saldo de efectivo disponible
        - Capital neto depositado
        - Valor de mercado de posiciones
        - Valor Liquidativo Total (NAV = Cash + Market Value)
        - P&L Realizado y No Realizado
        - Rentabilidad Total (%)
        """
        txs = self._load_transactions()
        cash = 0.0
        net_deposits = 0.0
        realized_pnl = 0.0
        dividends_total = 0.0

        # Rastrear costo promedio para calcular ganancias realizadas exactas al vender
        tracking_positions: Dict[str, Dict[str, float]] = {}

        for tx in txs:
            t_type = tx["type"]
            ticker = tx["ticker"]
            shares = float(tx.get("shares", 0))
            price = float(tx.get("price", 0))
            fee = float(tx.get("fee", 0))
            total = float(tx.get("total", 0))

            if t_type == "DEPOSIT":
                cash += total
                net_deposits += total
            elif t_type == "WITHDRAW":
                cash -= total
                net_deposits -= total
            elif t_type == "DIVIDEND":
                cash += total
                dividends_total += total
            elif t_type == "BUY":
                cash -= total
                if ticker not in tracking_positions:
                    tracking_positions[ticker] = {"shares": 0.0, "total_cost": 0.0}
                tracking_positions[ticker]["shares"] += shares
                tracking_positions[ticker]["total_cost"] += (shares * price) + fee
            elif t_type == "SELL":
                cash += total
                if ticker in tracking_positions and tracking_positions[ticker]["shares"] > 0:
                    current_shares = tracking_positions[ticker]["shares"]
                    avg_cost = tracking_positions[ticker]["total_cost"] / current_shares
                    cost_basis_sold = shares * avg_cost
                    # P&L realizado = Monto neto recibido - Costo base de los titulos vendidos
                    realized_pnl += (total - cost_basis_sold)
                    tracking_positions[ticker]["shares"] -= shares
                    tracking_positions[ticker]["total_cost"] -= cost_basis_sold
                    if tracking_positions[ticker]["shares"] <= 0.000001:
                        del tracking_positions[ticker]

        positions = self.get_positions()
        invested_capital = sum(p["total_cost"] for p in positions.values())
        positions_market_val = sum(p["market_value"] for p in positions.values())
        unrealized_pnl = sum(p["unrealized_pnl"] for p in positions.values())

        total_nav = cash + positions_market_val
        total_pnl = (total_nav - net_deposits) if net_deposits > 0 else 0.0
        total_return_pct = (total_pnl / net_deposits * 100) if net_deposits > 0 else 0.0

        # Calcular pesos relativos de cada posicion
        for p in positions.values():
            p["weight_pct"] = round((p["market_value"] / total_nav * 100), 2) if total_nav > 0 else 0.0

        cash_weight_pct = round((cash / total_nav * 100), 2) if total_nav > 0 else 0.0

        return {
            "portfolio_value": round(total_nav, 2),
            "cash_balance": round(cash, 2),
            "cash_weight_pct": cash_weight_pct,
            "invested_capital": round(invested_capital, 2),
            "positions_market_value": round(positions_market_val, 2),
            "net_deposits": round(net_deposits, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "dividends_total": round(dividends_total, 2),
            "positions_count": len(positions),
            "transactions_count": len(txs),
        }

    def get_transaction_history(self) -> List[Dict[str, Any]]:
        """Retorna todas las transacciones ordenadas de mas reciente a mas antigua."""
        txs = self._load_transactions()
        return list(reversed(txs))

    def export_backup(self, filepath: Optional[str] = None) -> str:
        """
        Exporta el portafolio completo (configuracion + transacciones) a un archivo JSON portable.
        Ideal para transferir a otro PC, respaldar en la nube o migrar.
        """
        if filepath is None:
            backup_dir = Path("exports") / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(backup_dir / f"portfolio_backup_{timestamp}.json")

        dest_path = Path(filepath)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        backup_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "config": self._load_config(),
            "transactions": self._load_transactions(),
        }

        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        return str(dest_path.resolve())

    def import_backup(self, filepath: str) -> Dict[str, Any]:
        """
        Restaura el portafolio a partir de un archivo JSON de respaldo.
        Sobrescribe el estado local con las transacciones y configuracion del respaldo.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"No se encontro el archivo de respaldo en: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "transactions" not in data or "config" not in data:
            raise ValueError("El archivo de respaldo no tiene el formato esperado (debe contener 'config' y 'transactions').")

        self._save_config(data["config"])
        self._save_transactions(data["transactions"])

        return {
            "restored_at": datetime.now().isoformat(),
            "transactions_count": len(data["transactions"]),
            "initial_cash": data["config"].get("initial_cash", 100_000.0),
        }

    def export_csv(self, filepath: Optional[str] = None) -> str:
        """
        Exporta el libro de transacciones a formato CSV para auditorias en Excel o Power BI.
        """
        import pandas as pd

        txs = self.get_transaction_history()
        if filepath is None:
            export_dir = Path("exports")
            export_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d")
            filepath = str(export_dir / f"portfolio_transactions_{timestamp}.csv")

        dest_path = Path(filepath)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(txs)
        if not df.empty:
            df.to_csv(dest_path, index=False, encoding="utf-8")
        else:
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write("id,timestamp,type,ticker,shares,price,fee,total,notes\n")

        return str(dest_path.resolve())

