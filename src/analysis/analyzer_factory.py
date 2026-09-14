from src.analysis.base_analyzer import AssetAnalyzer
from src.analysis.equity_analyzer import EquityAnalyzer
from src.analysis.reit_analyzer import REITAnalyzer
from src.analysis.etf_analyzer import EquityETFAnalyzer, BondETFAnalyzer


class AnalyzerFactory:
    """
    Factory Pattern para instanciar el analizador correcto segun el tipo de activo.

    Sigue el principio Open/Closed: para agregar un nuevo tipo de activo,
    solo se necesita crear una nueva clase que herede de AssetAnalyzer
    y registrarla en el diccionario _ANALYZERS.
    """

    _ANALYZERS = {
        "equity": EquityAnalyzer,
        "reit": REITAnalyzer,
        "equity_etf": EquityETFAnalyzer,
        "bond_etf": BondETFAnalyzer,
    }

    @classmethod
    def create(cls, ticker: str, data: dict, asset_type: str) -> AssetAnalyzer:
        """
        Crea e instancia el analizador apropiado segun el tipo de activo.

        Args:
            ticker: Simbolo del activo (ej. 'AAPL', 'TLT').
            data: Diccionario con los datos fundamentales descargados.
            asset_type: Tipo de activo ('equity', 'reit', 'equity_etf', 'bond_etf').

        Returns:
            Una instancia de la subclase de AssetAnalyzer correspondiente.

        Raises:
            ValueError: Si el tipo de activo no esta registrado.
        """
        analyzer_class = cls._ANALYZERS.get(asset_type)

        if analyzer_class is None:
            valid_types = list(cls._ANALYZERS.keys())
            raise ValueError(
                f"Tipo de activo no soportado: '{asset_type}'. "
                f"Tipos validos: {valid_types}"
            )

        return analyzer_class(ticker=ticker, data=data)

    @classmethod
    def get_supported_types(cls):
        """Retorna la lista de tipos de activos soportados."""
        return list(cls._ANALYZERS.keys())
