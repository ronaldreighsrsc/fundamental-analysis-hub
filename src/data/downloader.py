import os
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from typing import Dict, Any, Optional

class FinancialDataDownloader:
    def __init__(self, cache_dir: str = None, cache_expiry_hours: int = 24):
        if cache_dir is None:
            # Ruta de cache por defecto
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.cache_dir = os.path.join(base_dir, "data", "cache")
        else:
            self.cache_dir = cache_dir
            
        self.cache_expiry_hours = cache_expiry_hours
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_paths(self, ticker: str) -> Dict[str, str]:
        """Retorna las rutas de los archivos de cache para un ticker dado."""
        ticker_clean = ticker.strip().upper().replace("-", "_")
        return {
            "fundamentals": os.path.join(self.cache_dir, f"{ticker_clean}_fundamentals.json"),
            "prices": os.path.join(self.cache_dir, f"{ticker_clean}_prices.csv")
        }

    def _is_cache_valid(self, filepath: str) -> bool:
        """Verifica si el archivo de cache existe y no ha expirado."""
        if not os.path.exists(filepath):
            return False
            
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        age = datetime.now() - file_mtime
        return age < timedelta(hours=self.cache_expiry_hours)

    def _dataframe_to_dict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Convierte un DataFrame de yfinance (con fechas en indice/columnas) a un dict serializable en JSON."""
        if df is None or df.empty:
            return {}
            
        # Transponer para tener las fechas como indices de filas principales en el JSON
        df_transposed = df.transpose()
        
        # Convertir indices de fecha a strings YYYY-MM-DD
        df_transposed.index = df_transposed.index.map(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
        
        # Rellenar NaN con None para que se exporte como null en JSON
        df_clean = df_transposed.where(pd.notnull(df_transposed), None)
        
        return df_clean.to_dict(orient="index")

    def fetch_fundamental_data(self, ticker_symbol: str, force: bool = False) -> Dict[str, Any]:
        """
        Descarga los estados financieros y datos clave de un ticker.
        Si la cache local es valida, la lee directamente de disco.
        """
        ticker_symbol = ticker_symbol.strip().upper()
        paths = self._get_cache_paths(ticker_symbol)
        fund_path = paths["fundamentals"]

        if not force and self._is_cache_valid(fund_path):
            try:
                with open(fund_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                # Si falla leer la cache, re-descargamos
                pass

        # Si no es valida la cache o se fuerza la descarga, descargamos de yfinance
        ticker = yf.Ticker(ticker_symbol)
        
        # Intentamos obtener los datos fundamentales
        try:
            # Descargamos los estados financieros
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
            
            # Trimestrales
            q_income_stmt = ticker.quarterly_income_stmt
            q_balance_sheet = ticker.quarterly_balance_sheet
            q_cash_flow = ticker.quarterly_cashflow
            
            # Info general (P/E, Betas, etc)
            try:
                info = ticker.info
            except Exception:
                info = {}

            # Construimos la estructura de datos unificada
            data = {
                "ticker": ticker_symbol,
                "downloaded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "info": info,
                "annual": {
                    "income_statement": self._dataframe_to_dict(income_stmt),
                    "balance_sheet": self._dataframe_to_dict(balance_sheet),
                    "cash_flow": self._dataframe_to_dict(cash_flow)
                },
                "quarterly": {
                    "income_statement": self._dataframe_to_dict(q_income_stmt),
                    "balance_sheet": self._dataframe_to_dict(q_balance_sheet),
                    "cash_flow": self._dataframe_to_dict(q_cash_flow)
                }
            }

            # Guardamos en cache local
            with open(fund_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            return data

        except Exception as e:
            raise RuntimeError(f"Error al descargar datos fundamentales para {ticker_symbol}: {e}")

    def fetch_price_data(self, ticker_symbol: str, period: str = "5y", force: bool = False) -> pd.DataFrame:
        """
        Descarga los precios historicos diarios de cierre y los guarda en CSV.
        Si la cache local es valida, la lee directamente de disco.
        """
        ticker_symbol = ticker_symbol.strip().upper()
        paths = self._get_cache_paths(ticker_symbol)
        price_path = paths["prices"]

        if not force and self._is_cache_valid(price_path):
            try:
                return pd.read_csv(price_path, index_col="Date", parse_dates=True)
            except Exception:
                pass

        # Descarga precios
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(period=period)
            
            if df.empty:
                raise ValueError("No se encontraron precios para el periodo solicitado.")
                
            # Guardamos en cache local
            df.to_csv(price_path)
            return df
        except Exception as e:
            raise RuntimeError(f"Error al descargar precios historicos para {ticker_symbol}: {e}")
            
    def get_cached_fundamentals(self, ticker_symbol: str) -> Optional[Dict[str, Any]]:
        """Devuelve los fundamentales guardados en cache si existen, o None si no hay cache."""
        paths = self._get_cache_paths(ticker_symbol)
        fund_path = paths["fundamentals"]
        if os.path.exists(fund_path):
            try:
                with open(fund_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None
