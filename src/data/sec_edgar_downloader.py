import os
import json
import time
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class SecEdgarDownloader:
    """
    Cliente oficial para la API publica de la SEC (EDGAR).
    Permite obtener informes 10-K (anuales) y 10-Q (trimestrales) en formato XBRL
    de forma totalmente publica, gratuita y oficial sin necesidad de suscripciones.
    """

    SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SEC_FACTS_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    
    # Encabezado User-Agent requerido por la politica de uso de la SEC
    DEFAULT_USER_AGENT = "FundamentalAnalysisHub ResearchBot contact@fundamentalhub.local"

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_expiry_days: int = 7,
        user_agent: Optional[str] = None,
    ):
        if cache_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.cache_dir = os.path.join(base_dir, "data", "cache", "sec")
        else:
            self.cache_dir = cache_dir

        self.cache_expiry_days = cache_expiry_days
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        self.last_request_time = 0.0

        os.makedirs(self.cache_dir, exist_ok=True)
        self.tickers_cache_path = os.path.join(self.cache_dir, "sec_tickers.json")

    def _rate_limit(self):
        """Asegura respetar la politica de la SEC (maximo 10 solicitudes por segundo)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.15:  # ~6.6 solicitudes por segundo como maximo de seguridad
            time.sleep(0.15 - elapsed)
        self.last_request_time = time.time()

    def _is_cache_valid(self, filepath: str) -> bool:
        """Verifica si el archivo en cache existe y no ha expirado."""
        if not os.path.exists(filepath):
            return False
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        age = datetime.now() - file_mtime
        return age < timedelta(days=self.cache_expiry_days)

    def get_cik_for_ticker(self, ticker: str, force: bool = False) -> Optional[str]:
        """
        Resuelve el CIK (Central Index Key) de 10 digitos de la SEC para un ticker dado.
        """
        ticker_clean = ticker.strip().upper()

        # 1. Cargar mapeo de tickers desde cache si existe y es valido
        tickers_map = None
        if not force and self._is_cache_valid(self.tickers_cache_path):
            try:
                with open(self.tickers_cache_path, "r", encoding="utf-8") as f:
                    tickers_map = json.load(f)
            except Exception:
                tickers_map = None

        # 2. Descargar si no esta en cache
        if tickers_map is None:
            try:
                self._rate_limit()
                resp = requests.get(self.SEC_TICKERS_URL, headers=self.headers, timeout=15)
                if resp.status_code == 200:
                    raw_data = resp.json()
                    # Normalizar a diccionario {TICKER: CIK}
                    tickers_map = {}
                    for item in raw_data.values():
                        t = item.get("ticker", "").upper()
                        cik = str(item.get("cik_str", ""))
                        if t and cik:
                            tickers_map[t] = cik

                    with open(self.tickers_cache_path, "w", encoding="utf-8") as f:
                        json.dump(tickers_map, f, indent=2)
            except Exception as e:
                # Si falla la descarga y tenemos una version antigua, la usamos
                if os.path.exists(self.tickers_cache_path):
                    try:
                        with open(self.tickers_cache_path, "r", encoding="utf-8") as f:
                            tickers_map = json.load(f)
                    except Exception:
                        pass
                if not tickers_map:
                    raise RuntimeError(f"Error al descargar mapeo de CIKs de la SEC: {e}")

        # Retornar CIK con 10 digitos rellenos de ceros a la izquierda
        raw_cik = tickers_map.get(ticker_clean)
        if raw_cik:
            return str(raw_cik).zfill(10)
        return None

    def fetch_company_facts(self, ticker: str, force: bool = False) -> Dict[str, Any]:
        """
        Descarga el conjunto completo de hechos financieros XBRL (10-K y 10-Q) de una empresa.
        Lee de cache local si esta disponible.
        """
        ticker_clean = ticker.strip().upper()
        cache_path = os.path.join(self.cache_dir, f"{ticker_clean}_facts.json")

        if not force and self._is_cache_valid(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        cik = self.get_cik_for_ticker(ticker_clean)
        if not cik:
            raise ValueError(f"No se encontro el CIK de la SEC para el ticker: {ticker_clean}")

        url = self.SEC_FACTS_BASE_URL.format(cik=cik)
        self._rate_limit()
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=20)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"La SEC retorno codigo {resp.status_code} al solicitar CIK {cik} ({ticker_clean})"
                )

            data = resp.json()

            # Guardar en cache local
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return data

        except Exception as e:
            raise RuntimeError(f"Error al descargar hechos financieros de la SEC para {ticker_clean}: {e}")
