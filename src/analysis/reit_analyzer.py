from typing import Dict, Any, List
from src.analysis.base_analyzer import AssetAnalyzer


class REITAnalyzer(AssetAnalyzer):
    """
    Analizador para REITs (Real Estate Investment Trusts).

    Los REITs no se evaluan con EPS tradicional ni P/E convencional.
    Sus metricas clave son:
    - FFO (Funds From Operations): Ingreso neto + depreciacion - ganancia por venta de propiedades.
    - AFFO (Adjusted FFO): FFO ajustado por gastos de capital recurrentes.
    - Dividend Yield y Payout Ratio calculado sobre FFO (no sobre EPS).
    - NAV (Net Asset Value): Valor neto de los activos inmobiliarios.
    """

    def __init__(self, ticker: str, data: dict):
        super().__init__(ticker, data)
        self.annual = data.get("annual", {})
        self.quarterly = data.get("quarterly", {})

    def get_asset_type(self) -> str:
        return "reit"

    def _get_annual_years(self) -> List[str]:
        """Retorna las fechas de los periodos anuales disponibles."""
        income = self.annual.get("income_statement", {})
        return sorted(income.keys(), reverse=True)

    def _calc_ffo(self, year: str) -> float:
        """
        FFO = Net Income + Depreciation & Amortization - Gains on Sale of Properties.
        
        yfinance no provee FFO directamente, asi que lo estimamos
        a partir del Income Statement y Cash Flow Statement.
        """
        inc = self.annual.get("income_statement", {}).get(year, {})
        cf = self.annual.get("cash_flow", {}).get(year, {})

        net_income = inc.get("Net Income") or 0
        # Depreciacion y amortizacion (viene en el cash flow como positivo)
        depreciation = cf.get("Depreciation And Amortization") or inc.get("Reconciled Depreciation") or 0

        # Ganancia por venta de activos (si existe, se resta)
        gain_on_sale = cf.get("Gain On Sale Of Property Plant Equipment") or 0

        ffo = net_income + abs(depreciation) - gain_on_sale
        return ffo

    def _calc_affo(self, year: str) -> float:
        """
        AFFO = FFO - Capital Expenditures recurrentes (mantenimiento).
        
        Usamos Capital Expenditure del Cash Flow como proxy.
        """
        ffo = self._calc_ffo(year)
        cf = self.annual.get("cash_flow", {}).get(year, {})
        capex = cf.get("Capital Expenditure") or 0
        # CapEx viene como negativo en yfinance
        affo = ffo + capex  # capex es negativo, asi que sumamos
        return affo

    def _calc_ffo_payout_ratio(self, year: str) -> float:
        """
        Payout Ratio basado en FFO = Dividendos Totales Pagados / FFO.
        Un REIT sano deberia pagar menos del 85% de su FFO en dividendos.
        """
        cf = self.annual.get("cash_flow", {}).get(year, {})
        ffo = self._calc_ffo(year)
        dividends_paid = (
            cf.get("Common Stock Dividend Paid")
            or cf.get("Cash Dividends Paid")
            or 0
        )

        if ffo <= 0:
            return 0.0

        return abs(dividends_paid) / ffo

    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Retorna las metricas clave de un REIT:
        FFO, AFFO, Payout Ratio sobre FFO, Dividend Yield, Debt/Equity.
        """
        years = self._get_annual_years()[:4]

        ffo_by_year = {}
        for yr in years:
            ffo = self._calc_ffo(yr)
            affo = self._calc_affo(yr)
            payout = self._calc_ffo_payout_ratio(yr)
            ffo_by_year[yr] = {
                "ffo": round(ffo, 2),
                "affo": round(affo, 2),
                "ffo_payout_ratio": round(payout, 4),
            }

        return {
            "ffo_analysis": ffo_by_year,
            "valuation": {
                "price_to_book": self.info.get("priceToBook"),
                "price_to_sales": self.info.get("priceToSalesTrailing12Months"),
                "ev_to_revenue": self.info.get("enterpriseToRevenue"),
            },
            "dividends": {
                "dividend_yield": self.info.get("dividendYield"),
                "dividend_rate": self.info.get("dividendRate"),
                "payout_ratio_eps": self.info.get("payoutRatio"),
            },
            "debt": {
                "debt_to_equity": self.info.get("debtToEquity"),
                "current_ratio": self.info.get("currentRatio"),
            },
            "occupancy_proxy": {
                "revenue_growth": self.info.get("revenueGrowth"),
                "operating_margins": self.info.get("operatingMargins"),
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Resumen ejecutivo rapido del REIT."""
        years = self._get_annual_years()
        latest_ffo = self._calc_ffo(years[0]) if years else 0

        return {
            "ticker": self.ticker,
            "name": self.get_name(),
            "type": self.get_asset_type(),
            "sector": self.get_sector(),
            "price": self.get_current_price(),
            "dividend_yield": self.info.get("dividendYield"),
            "latest_ffo": round(latest_ffo, 2),
            "price_to_book": self.info.get("priceToBook"),
            "debt_to_equity": self.info.get("debtToEquity"),
        }


# Alias de conveniencia
ReitAnalyzer = REITAnalyzer

