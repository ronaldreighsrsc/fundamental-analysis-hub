import json
import os
from typing import List, Dict

# Tipos validos de activos en la watchlist
VALID_ASSET_TYPES = ["equity", "reit", "equity_etf", "bond_etf"]

class WatchlistManager:
    def __init__(self, filepath: str = None):
        if filepath is None:
            # Ruta por defecto relativa a la raiz del proyecto
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.filepath = os.path.join(base_dir, "config", "watchlist.json")
        else:
            self.filepath = filepath
            
        self.watchlist: List[Dict[str, str]] = []
        self.load()

    def load(self) -> List[Dict[str, str]]:
        """Carga la lista de vigilancia desde el archivo JSON."""
        if not os.path.exists(self.filepath):
            # Si el archivo no existe, crea un directorio base y guarda una lista vacia
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.save()
            return self.watchlist

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.watchlist = json.load(f)
        except json.JSONDecodeError:
            self.watchlist = []
            
        return self.watchlist

    def save(self) -> None:
        """Guarda el estado actual de la watchlist en el archivo JSON."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.watchlist, f, indent=2, ensure_ascii=False)

    def get_tickers(self) -> List[str]:
        """Retorna una lista simple de los simbolos de los tickers (ej. ['AAPL', 'MSFT'])."""
        return [item["ticker"].upper() for item in self.watchlist]

    def get_watchlist(self) -> List[Dict[str, str]]:
        """Retorna la lista completa de acciones con sus metadatos (nombre, sector, tipo)."""
        return self.watchlist

    def get_tickers_by_type(self, asset_type: str) -> List[str]:
        """Retorna los simbolos filtrados por tipo de activo (equity, reit, equity_etf, bond_etf)."""
        return [
            item["ticker"].upper()
            for item in self.watchlist
            if item.get("type", "equity") == asset_type
        ]

    def get_watchlist_by_type(self, asset_type: str) -> List[Dict[str, str]]:
        """Retorna la lista completa filtrada por tipo de activo."""
        return [
            item for item in self.watchlist
            if item.get("type", "equity") == asset_type
        ]

    def add_ticker(self, ticker: str, name: str = "", sector: str = "", asset_type: str = "equity") -> bool:
        """
        Agrega un nuevo ticker a la watchlist.
        Retorna True si se agrego con exito, False si ya existia.
        El tipo de activo debe ser uno de: equity, reit, equity_etf, bond_etf.
        """
        ticker_upper = ticker.strip().upper()
        if not ticker_upper:
            return False

        if asset_type not in VALID_ASSET_TYPES:
            raise ValueError(f"Tipo de activo invalido: '{asset_type}'. Opciones: {VALID_ASSET_TYPES}")

        if ticker_upper in self.get_tickers():
            return False
            
        self.watchlist.append({
            "ticker": ticker_upper,
            "name": name.strip(),
            "sector": sector.strip(),
            "type": asset_type
        })
        self.save()
        return True

    def remove_ticker(self, ticker: str) -> bool:
        """
        Elimina un ticker de la watchlist.
        Retorna True si se elimino con exito, False si no se encontro.
        """
        ticker_upper = ticker.strip().upper()
        initial_length = len(self.watchlist)
        self.watchlist = [item for item in self.watchlist if item["ticker"].upper() != ticker_upper]
        
        if len(self.watchlist) < initial_length:
            self.save()
            return True
        return False
