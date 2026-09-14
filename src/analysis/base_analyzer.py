from abc import ABC, abstractmethod
from typing import Dict, Any


class AssetAnalyzer(ABC):
    """
    Clase abstracta base para todos los analizadores de activos.

    Cada tipo de activo (equity, REIT, ETF de renta variable, ETF de renta fija)
    debe implementar esta interfaz. Esto garantiza que el orquestador y el factory
    puedan trabajar con cualquier tipo de activo de forma uniforme (Liskov Substitution).
    """

    def __init__(self, ticker: str, data: dict):
        self.ticker = ticker.upper()
        self.data = data
        self.info = data.get("info", {})

    @abstractmethod
    def get_asset_type(self) -> str:
        """Retorna el tipo de activo como string (equity, reit, equity_etf, bond_etf)."""
        pass

    @abstractmethod
    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Retorna un diccionario con las metricas clave del activo.
        Las metricas varian segun el tipo de activo.
        """
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """
        Retorna un resumen general del activo con la informacion mas relevante
        para mostrar en un dashboard o tabla.
        """
        pass

    def get_current_price(self) -> float:
        """Retorna el precio actual del activo."""
        return self.info.get("currentPrice") or self.info.get("regularMarketPrice") or 0.0

    def get_name(self) -> str:
        """Retorna el nombre largo del activo."""
        return self.info.get("longName") or self.info.get("shortName") or self.ticker

    def get_sector(self) -> str:
        """Retorna el sector del activo."""
        return self.info.get("sector") or self.info.get("category") or "N/A"
