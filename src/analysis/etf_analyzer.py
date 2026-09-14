from typing import Dict, Any
from src.analysis.base_analyzer import AssetAnalyzer


class EquityETFAnalyzer(AssetAnalyzer):
    """
    Analizador para ETFs de renta variable (JEPI, SCHD, VNQ, XLU).

    Los ETFs no tienen estados financieros propios (no son empresas).
    Se evaluan por:
    - Expense Ratio (costo anual del fondo)
    - Dividend Yield (rendimiento por dividendos)
    - Total Return y Performance vs Benchmark
    - Top Holdings y Sector Allocation
    - Beta y volatilidad
    """

    def __init__(self, ticker: str, data: dict):
        super().__init__(ticker, data)

    def get_asset_type(self) -> str:
        return "equity_etf"

    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Metricas clave para un ETF de renta variable.
        La mayoria proviene directamente del campo 'info' de yfinance.
        """
        return {
            "fund_overview": {
                "category": self.info.get("category"),
                "fund_family": self.info.get("fundFamily"),
                "total_assets": self.info.get("totalAssets"),
                "expense_ratio": self.info.get("annualReportExpenseRatio"),
            },
            "performance": {
                "ytd_return": self.info.get("ytdReturn"),
                "three_year_return": self.info.get("threeYearAverageReturn"),
                "five_year_return": self.info.get("fiveYearAverageReturn"),
                "beta_3y": self.info.get("beta3Year"),
            },
            "dividends": {
                "dividend_yield": self.info.get("yield") or self.info.get("dividendYield"),
                "dividend_rate": self.info.get("dividendRate"),
                "trailing_annual_yield": self.info.get("trailingAnnualDividendYield"),
            },
            "risk": {
                "beta": self.info.get("beta3Year"),
                "52_week_high": self.info.get("fiftyTwoWeekHigh"),
                "52_week_low": self.info.get("fiftyTwoWeekLow"),
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Resumen ejecutivo rapido del ETF de renta variable."""
        return {
            "ticker": self.ticker,
            "name": self.get_name(),
            "type": self.get_asset_type(),
            "category": self.info.get("category"),
            "price": self.get_current_price(),
            "expense_ratio": self.info.get("annualReportExpenseRatio"),
            "dividend_yield": self.info.get("yield") or self.info.get("dividendYield"),
            "total_assets": self.info.get("totalAssets"),
            "ytd_return": self.info.get("ytdReturn"),
        }


class BondETFAnalyzer(AssetAnalyzer):
    """
    Analizador para ETFs de renta fija / bonos (TLT, IEF, SHY, VCIT).

    Se evaluan por:
    - Yield (rendimiento)
    - Duration (sensibilidad a tasas de interes)
    - Credit Quality (calidad crediticia)
    - Expense Ratio
    - Estos ETFs NO tienen Income Statement, Balance Sheet ni Cash Flow.
    """

    def __init__(self, ticker: str, data: dict):
        super().__init__(ticker, data)

    def get_asset_type(self) -> str:
        return "bond_etf"

    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Metricas clave para un ETF de bonos.
        """
        return {
            "fund_overview": {
                "category": self.info.get("category"),
                "fund_family": self.info.get("fundFamily"),
                "total_assets": self.info.get("totalAssets"),
                "expense_ratio": self.info.get("annualReportExpenseRatio"),
            },
            "yield_analysis": {
                "yield": self.info.get("yield"),
                "dividend_yield": self.info.get("dividendYield"),
                "dividend_rate": self.info.get("dividendRate"),
                "trailing_annual_yield": self.info.get("trailingAnnualDividendYield"),
            },
            "performance": {
                "ytd_return": self.info.get("ytdReturn"),
                "three_year_return": self.info.get("threeYearAverageReturn"),
                "five_year_return": self.info.get("fiveYearAverageReturn"),
            },
            "risk": {
                "beta": self.info.get("beta3Year"),
                "52_week_high": self.info.get("fiftyTwoWeekHigh"),
                "52_week_low": self.info.get("fiftyTwoWeekLow"),
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Resumen ejecutivo rapido del ETF de bonos."""
        return {
            "ticker": self.ticker,
            "name": self.get_name(),
            "type": self.get_asset_type(),
            "category": self.info.get("category"),
            "price": self.get_current_price(),
            "expense_ratio": self.info.get("annualReportExpenseRatio"),
            "yield": self.info.get("yield"),
            "total_assets": self.info.get("totalAssets"),
            "ytd_return": self.info.get("ytdReturn"),
        }


# Aliases de conveniencia
EquityEtfAnalyzer = EquityETFAnalyzer
BondEtfAnalyzer = BondETFAnalyzer

