import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
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
        Obtiene el precio actual de mercado en tiempo real de un ticker desde yfinance.
        Si la llamada falla o se esta sin conexion, utiliza la cache local como respaldo.
        """
        ticker_clean = ticker.strip().upper()

        # 1. Intentar desde yfinance en vivo (tiempo real / fast_info)
        try:
            t = yf.Ticker(ticker_clean)
            fast_info = getattr(t, "fast_info", None)
            if fast_info is not None:
                last_p = fast_info.get("lastPrice") or fast_info.get("previousClose")
                if last_p and float(last_p) > 0:
                    return float(last_p)

            q_type = str(getattr(fast_info, "quote_type", "")).upper() if fast_info else ""
            if q_type != "ETF":
                info = t.info or {}
                p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                if p and float(p) > 0:
                    return float(p)
        except Exception:
            pass

        # 2. Respaldo de contingencia: cache local de fundamentales
        cached = self.downloader.get_cached_fundamentals(ticker_clean)
        if cached:
            info = cached.get("info", {})
            p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if p and float(p) > 0:
                return float(p)

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

    def simulate_monthly_deposits(
        self,
        monthly_amount: float = 500.0,
        months: int = 1,
        start_date: Optional[str] = "2026-10-01",
        day_of_month: int = 1,
        notes: str = "Aporte mensual DCA (día 1)",
    ) -> List[Dict[str, Any]]:
        """
        Registra o simula una serie de aportes mensuales recurrentes el dia 1 de cada mes,
        iniciando en una fecha especifica (por defecto 2026-10-01).
        Permite evaluar el efecto de Dollar Cost Averaging (DCA) y separar aportes de rentabilidad.
        """
        if monthly_amount <= 0:
            raise ValueError("El monto mensual debe ser mayor a 0.")
        if months <= 0:
            raise ValueError("La cantidad de meses debe ser al menos 1.")

        created_txs = []
        txs = self._load_transactions()

        if start_date:
            try:
                base_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
            except Exception:
                base_dt = datetime(2026, 10, 1)
        else:
            base_dt = datetime(2026, 10, 1)

        start_year = base_dt.year
        start_month = base_dt.month
        target_day = max(1, min(28, day_of_month))

        for i in range(months):
            total_months = (start_month - 1) + i
            y = start_year + (total_months // 12)
            m = (total_months % 12) + 1
            tx_time = datetime(y, m, target_day, 9, 0, 0)

            tx = {
                "id": str(uuid.uuid4()),
                "timestamp": tx_time.isoformat(),
                "type": "DEPOSIT",
                "ticker": "CASH",
                "shares": 1.0,
                "price": float(monthly_amount),
                "fee": 0.0,
                "total": float(monthly_amount),
                "notes": f"{notes} ({m:02d}/{y})",
            }
            txs.append(tx)
            created_txs.append(tx)

        # Reordenar cronologicamente
        txs.sort(key=lambda x: x.get("timestamp", ""))
        self._save_transactions(txs)
        return created_txs



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

    def record_split(
        self,
        ticker: str,
        ratio: float,
        split_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra un desdoblamiento de acciones (Stock Split / Reverse Split).
        ratio: factor multiplicador de acciones (ej. 4.0 para 4:1, 10.0 para 10:1, 0.5 para 1:2).
        """
        ticker_clean = ticker.strip().upper()
        if ratio <= 0:
            raise ValueError("El ratio de split debe ser un valor positivo mayor a 0.")

        positions = self.get_positions()
        if ticker_clean not in positions or positions[ticker_clean]["shares"] <= 0:
            raise ValueError(f"No posees acciones de {ticker_clean} para aplicar un split.")

        txs = self._load_transactions()
        timestamp = split_date if split_date else datetime.now().isoformat()
        if notes is None:
            notes = f"Desdoblamiento corporativo (Split) {ratio:g}:1"

        tx = {
            "id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "type": "SPLIT",
            "ticker": ticker_clean,
            "shares": float(ratio),
            "price": 0.0,
            "fee": 0.0,
            "total": 0.0,
            "notes": notes,
        }
        txs.append(tx)
        txs.sort(key=lambda x: x.get("timestamp", ""))
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

            elif t_type == "SPLIT":
                split_ratio = float(tx.get("shares", 1.0))
                if ticker in raw_positions and raw_positions[ticker]["shares"] > 0 and split_ratio > 0:
                    raw_positions[ticker]["shares"] *= split_ratio

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
            elif t_type == "SPLIT":
                split_ratio = float(tx.get("shares", 1.0))
                if ticker in tracking_positions and tracking_positions[ticker]["shares"] > 0 and split_ratio > 0:
                    tracking_positions[ticker]["shares"] *= split_ratio

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

    def sync_corporate_actions(self) -> Dict[str, Any]:
        """
        Escanea y sincroniza de forma automatica e idempotente los eventos corporativos
        (Stock Splits y Dividendos en efectivo con fechas de corte Ex-Date) para todos los
        activos operados en el portafolio.
        """
        txs = self._load_transactions()
        tickers = sorted(list({tx.get("ticker", "") for tx in txs if tx.get("ticker") not in ("", "CASH")}))

        applied_splits = []
        applied_dividends = []

        for ticker in tickers:
            ticker_txs = [t for t in txs if t.get("ticker") == ticker]
            if not ticker_txs:
                continue

            buy_txs = [t for t in ticker_txs if t.get("type") == "BUY"]
            if not buy_txs:
                continue

            earliest_buy = min(t.get("timestamp", "")[:10] for t in buy_txs)
            try:
                earliest_date = datetime.strptime(earliest_buy, "%Y-%m-%d").date()
            except Exception:
                continue

            try:
                t_obj = yf.Ticker(ticker)
                actions = t_obj.actions
            except Exception:
                continue

            if actions is None or actions.empty:
                continue

            def _calc_shares_before(cutoff_date_str: str) -> float:
                sh = 0.0
                for t in txs:
                    if t.get("ticker") != ticker:
                        continue
                    t_date = t.get("timestamp", "")[:10]
                    if t_date >= cutoff_date_str:
                        continue
                    t_type = t.get("type")
                    if t_type == "BUY":
                        sh += float(t.get("shares", 0.0))
                    elif t_type == "SELL":
                        sh = max(0.0, sh - float(t.get("shares", 0.0)))
                    elif t_type == "SPLIT":
                        sh *= float(t.get("shares", 1.0))
                return round(sh, 6)

            for idx, row in actions.iterrows():
                try:
                    action_date = idx.date()
                except Exception:
                    continue

                if action_date < earliest_date:
                    continue

                action_date_str = str(action_date)

                # 1. Desdoblamientos (Splits)
                split_val = float(row.get("Stock Splits", 0.0))
                if split_val > 0.0 and split_val != 1.0:
                    already_logged = any(
                        t.get("type") == "SPLIT" and
                        t.get("ticker") == ticker and
                        t.get("timestamp", "")[:10] == action_date_str
                        for t in txs
                    )
                    if not already_logged:
                        shares_held = _calc_shares_before(action_date_str)
                        if shares_held > 0.0001:
                            new_tx = {
                                "id": str(uuid.uuid4()),
                                "timestamp": f"{action_date_str}T09:30:00",
                                "type": "SPLIT",
                                "ticker": ticker,
                                "shares": split_val,
                                "price": 0.0,
                                "fee": 0.0,
                                "total": 0.0,
                                "notes": f"Desdoblamiento corporativo (Split) {split_val:g}:1 (Ex-Date: {action_date_str})",
                            }
                            txs.append(new_tx)
                            applied_splits.append({
                                "ticker": ticker,
                                "date": action_date_str,
                                "ratio": split_val,
                                "shares_before": shares_held,
                                "shares_after": round(shares_held * split_val, 4),
                            })

                # 2. Dividendos en Efectivo
                div_val = float(row.get("Dividends", 0.0))
                if div_val > 0.0:
                    already_logged = any(
                        t.get("type") == "DIVIDEND" and
                        t.get("ticker") == ticker and
                        (t.get("timestamp", "")[:10] == action_date_str or f"Ex-Date: {action_date_str}" in t.get("notes", ""))
                        for t in txs
                    )
                    if not already_logged:
                        shares_held = _calc_shares_before(action_date_str)
                        if shares_held > 0.0001:
                            total_div = round(shares_held * div_val, 2)
                            new_tx = {
                                "id": str(uuid.uuid4()),
                                "timestamp": f"{action_date_str}T16:00:00",
                                "type": "DIVIDEND",
                                "ticker": ticker,
                                "shares": round(shares_held, 4),
                                "price": round(div_val, 4),
                                "fee": 0.0,
                                "total": total_div,
                                "notes": f"Dividendo automático {ticker}: {shares_held:g} accs × ${div_val:.4f} (Ex-Date: {action_date_str})",
                            }
                            txs.append(new_tx)
                            applied_dividends.append({
                                "ticker": ticker,
                                "date": action_date_str,
                                "dps": round(div_val, 4),
                                "shares": round(shares_held, 4),
                                "total": total_div,
                            })

        if applied_splits or applied_dividends:
            txs.sort(key=lambda x: x.get("timestamp", ""))
            self._save_transactions(txs)

        total_credited = round(sum(d["total"] for d in applied_dividends), 2)
        return {
            "applied_splits": applied_splits,
            "applied_dividends": applied_dividends,
            "total_splits_count": len(applied_splits),
            "total_dividends_count": len(applied_dividends),
            "total_dividends_credited": total_credited,
        }

    def get_dividend_calendar(self) -> Dict[str, Any]:
        """
        Calcula el calendario proyectado de dividendos para las posiciones abiertas,
        junto con métricas de Dividend Yield y Yield on Cost (YoC).
        """
        positions = self.get_positions()
        summary = self.get_summary()
        port_val = summary["portfolio_value"]

        holdings_dividends = []
        total_annual_income = 0.0

        today = datetime.now().date()
        months_proj = {}
        for m_offset in range(12):
            tot_m = (today.month - 1) + m_offset
            y = today.year + (tot_m // 12)
            m = (tot_m % 12) + 1
            key = f"{y}-{m:02d}"
            months_proj[key] = 0.0

        for ticker, pos in positions.items():
            shares = pos["shares"]
            if shares <= 0:
                continue
            avg_cost = pos["avg_cost"]
            curr_price = pos["current_price"]

            dps = 0.0
            div_yield = 0.0
            ex_date_str = "N/A"
            pay_date_str = "N/A"

            try:
                t_obj = yf.Ticker(ticker)
                q_type = ""
                try:
                    q_type = str(getattr(t_obj.fast_info, "quote_type", "")).upper()
                except Exception:
                    pass

                info = {}
                if q_type != "ETF":
                    try:
                        info = t_obj.info or {}
                    except Exception:
                        info = {}

                dps = float(info.get("dividendRate") or 0.0)
                div_yield = float(info.get("dividendYield") or 0.0) * 100

                if dps <= 0.0:
                    divs = t_obj.dividends
                    if divs is not None and not divs.empty:
                        try:
                            recent = divs.tail(12 if q_type == "ETF" else 4)
                            dps = float(recent.sum())
                            if curr_price > 0:
                                div_yield = (dps / curr_price) * 100
                        except Exception:
                            pass

                cal = None
                if q_type != "ETF":
                    try:
                        cal = t_obj.calendar
                    except Exception:
                        cal = None

                if cal:
                    if "Ex-Dividend Date" in cal and cal["Ex-Dividend Date"]:
                        ex_date_str = str(cal["Ex-Dividend Date"])
                    if "Dividend Date" in cal and cal["Dividend Date"]:
                        pay_date_str = str(cal["Dividend Date"])
            except Exception:
                pass

            annual_income = round(shares * dps, 2)
            total_annual_income += annual_income

            yoc = round((dps / avg_cost * 100), 2) if avg_cost > 0 else 0.0

            if annual_income > 0:
                quarterly_payout = round(annual_income / 4.0, 2)
                q_months = [(today.month - 1 + i * 3) % 12 + 1 for i in range(4)]
                for m_key in months_proj:
                    m_num = int(m_key.split("-")[1])
                    if m_num in q_months:
                        months_proj[m_key] = round(months_proj[m_key] + quarterly_payout, 2)

            holdings_dividends.append({
                "ticker": ticker,
                "shares": shares,
                "dps": round(dps, 4),
                "annual_income": annual_income,
                "dividend_yield_pct": round(div_yield, 2),
                "yield_on_cost_pct": yoc,
                "ex_dividend_date": ex_date_str,
                "pay_date": pay_date_str,
            })

        portfolio_dividend_yield = round((total_annual_income / port_val * 100), 2) if port_val > 0 else 0.0

        return {
            "portfolio_annual_income": round(total_annual_income, 2),
            "portfolio_dividend_yield_pct": portfolio_dividend_yield,
            "monthly_projections": months_proj,
            "holdings": holdings_dividends,
        }

