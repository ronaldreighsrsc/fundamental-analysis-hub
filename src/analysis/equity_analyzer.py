import numpy as np
from typing import Dict, Any, List
from src.analysis.base_analyzer import AssetAnalyzer


class EquityAnalyzer(AssetAnalyzer):
    """
    Analizador para acciones individuales (equities).

    Calcula metricas fundamentales clasicas del value investing:
    margenes operativos, ROIC, crecimiento de EPS, Free Cash Flow, ratios de
    valoracion (P/E, P/B, EV/EBITDA), y niveles de endeudamiento.
    """

    def __init__(self, ticker: str, data: dict):
        super().__init__(ticker, data)
        self.annual = data.get("annual", {})
        self.quarterly = data.get("quarterly", {})

    def get_asset_type(self) -> str:
        return "equity"

    # =========================================================================
    # Metricas de Rentabilidad
    # =========================================================================

    def _get_annual_years(self) -> List[str]:
        """Retorna las fechas de los periodos anuales disponibles, ordenadas de mas reciente a mas antigua."""
        income = self.annual.get("income_statement", {})
        return sorted(income.keys(), reverse=True)

    def _calc_gross_margin(self, year: str) -> float:
        """Margen Bruto = Gross Profit / Total Revenue."""
        inc = self.annual.get("income_statement", {}).get(year, {})
        revenue = inc.get("Total Revenue")
        gross_profit = inc.get("Gross Profit")
        if not revenue or not gross_profit or revenue == 0:
            return 0.0
        return gross_profit / revenue

    def _calc_operating_margin(self, year: str) -> float:
        """Margen Operativo = Operating Income / Total Revenue."""
        inc = self.annual.get("income_statement", {}).get(year, {})
        revenue = inc.get("Total Revenue")
        operating = inc.get("Operating Income") or inc.get("EBIT")
        if not revenue or not operating or revenue == 0:
            return 0.0
        return operating / revenue

    def _calc_net_margin(self, year: str) -> float:
        """Margen Neto = Net Income / Total Revenue."""
        inc = self.annual.get("income_statement", {}).get(year, {})
        revenue = inc.get("Total Revenue")
        net_income = inc.get("Net Income")
        if not revenue or not net_income or revenue == 0:
            return 0.0
        return net_income / revenue

    def _calc_fcf_margin(self, year: str) -> float:
        """Margen de Flujo de Caja Libre = Free Cash Flow / Total Revenue."""
        inc = self.annual.get("income_statement", {}).get(year, {})
        cf = self.annual.get("cash_flow", {}).get(year, {})
        revenue = inc.get("Total Revenue")
        fcf = cf.get("Free Cash Flow")
        if not revenue or not fcf or revenue == 0:
            return 0.0
        return fcf / revenue

    def _calc_roic(self, year: str) -> float:
        """
        ROIC = NOPAT / Capital Invertido.
        NOPAT = EBIT * (1 - Tax Rate)
        Capital Invertido = Total Debt + Stockholders Equity - Cash
        """
        inc = self.annual.get("income_statement", {}).get(year, {})
        bal = self.annual.get("balance_sheet", {}).get(year, {})

        ebit = inc.get("EBIT") or inc.get("Operating Income")
        tax_rate = inc.get("Tax Rate For Calcs")
        if tax_rate is None or tax_rate != tax_rate:  # NaN check
            tax_rate = 0.21

        if not ebit:
            return 0.0

        nopat = ebit * (1 - tax_rate)

        total_debt = bal.get("Total Debt") or 0
        equity = bal.get("Stockholders Equity") or bal.get("Total Equity Gross Minority Interest") or 0
        cash = bal.get("Cash And Cash Equivalents") or 0

        invested_capital = total_debt + equity - cash
        if invested_capital <= 0:
            return 0.0

        return nopat / invested_capital

    # =========================================================================
    # Metricas de Valoracion (desde info de yfinance)
    # =========================================================================

    def _get_valuation_ratios(self) -> Dict[str, Any]:
        """Ratios de valoracion disponibles directamente en la info de yfinance."""
        return {
            "pe_trailing": self.info.get("trailingPE"),
            "pe_forward": self.info.get("forwardPE"),
            "peg_ratio": self.info.get("pegRatio"),
            "price_to_book": self.info.get("priceToBook"),
            "price_to_sales": self.info.get("priceToSalesTrailing12Months"),
            "ev_to_ebitda": self.info.get("enterpriseToEbitda"),
            "ev_to_revenue": self.info.get("enterpriseToRevenue"),
        }

    # =========================================================================
    # Metricas de Endeudamiento y Liquidez
    # =========================================================================

    def _get_debt_metrics(self) -> Dict[str, Any]:
        """Metricas de deuda y liquidez."""
        return {
            "debt_to_equity": self.info.get("debtToEquity"),
            "current_ratio": self.info.get("currentRatio"),
            "quick_ratio": self.info.get("quickRatio"),
        }

    # =========================================================================
    # Metricas de Dividendos
    # =========================================================================

    def _get_dividend_metrics(self) -> Dict[str, Any]:
        """Informacion de dividendos."""
        return {
            "dividend_yield": self.info.get("dividendYield"),
            "dividend_rate": self.info.get("dividendRate"),
            "payout_ratio": self.info.get("payoutRatio"),
        }

    # =========================================================================
    # Metricas de Inversores y Propiedad (Skin in the Game)
    # =========================================================================

    def _get_ownership_metrics(self) -> Dict[str, Any]:
        """Metricas de estructura de propiedad accionaria (Insiders e Institucionales)."""
        return {
            "held_percent_insiders": self.info.get("heldPercentInsiders"),
            "held_percent_institutions": self.info.get("heldPercentInstitutions"),
        }

    def get_moat_analysis(self) -> Dict[str, Any]:
        """
        Retorna la evaluacion cualitativa del Moat (foso economico), fuentes
        de ventaja competitiva, tesis del inversor y amenazas de disrupcion.
        """
        from src.analysis.moat_manager import MoatManager
        mgr = MoatManager()
        moat_info = mgr.get_moat(self.ticker)
        if not moat_info:
            return {
                "has_thesis": False,
                "rating": "None",
                "trend": "Stable",
                "sources": [],
                "thesis": "Pendiente de documentacion cualitativa.",
                "threats": "Pendiente de analisis de riesgos de disrupcion.",
            }
        return {
            "has_thesis": True,
            **moat_info
        }

    # =========================================================================
    # Interfaz Publica (implementacion de AssetAnalyzer)
    # =========================================================================

    def get_key_metrics(self) -> Dict[str, Any]:
        """
        Retorna todas las metricas clave del equity organizadas por categoria.
        Incluye margenes historicos (ultimos 4 anios), ROIC, ratios de valoracion,
        endeudamiento, dividendos, estructura de propiedad y evaluacion de Moat.
        """
        years = self._get_annual_years()[:4]

        # Calcular metricas historicas por anio
        margins_by_year = {}
        roics = []
        for yr in years:
            margins_by_year[yr] = {
                "gross_margin": round(self._calc_gross_margin(yr), 4),
                "operating_margin": round(self._calc_operating_margin(yr), 4),
                "net_margin": round(self._calc_net_margin(yr), 4),
                "fcf_margin": round(self._calc_fcf_margin(yr), 4),
            }
            roics.append(self._calc_roic(yr))

        # Promedios
        gross_margins = [m["gross_margin"] for m in margins_by_year.values()]
        avg_gross_margin = float(np.mean(gross_margins)) if gross_margins else 0.0
        avg_roic = float(np.mean(roics)) if roics else 0.0

        return {
            "profitability": {
                "margins_by_year": margins_by_year,
                "avg_gross_margin": round(avg_gross_margin, 4),
                "avg_roic": round(avg_roic, 4),
                "roe": self.info.get("returnOnEquity"),
                "roa": self.info.get("returnOnAssets"),
            },
            "valuation": self._get_valuation_ratios(),
            "debt": self._get_debt_metrics(),
            "dividends": self._get_dividend_metrics(),
            "ownership": self._get_ownership_metrics(),
            "moat": self.get_moat_analysis(),
            "growth": {
                "earnings_growth": self.info.get("earningsGrowth"),
                "revenue_growth": self.info.get("revenueGrowth"),
                "earnings_quarterly_growth": self.info.get("earningsQuarterlyGrowth"),
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """Resumen ejecutivo rapido del equity."""
        return {
            "ticker": self.ticker,
            "name": self.get_name(),
            "type": self.get_asset_type(),
            "sector": self.get_sector(),
            "price": self.get_current_price(),
            "market_cap": self.info.get("marketCap"),
            "pe_trailing": self.info.get("trailingPE"),
            "dividend_yield": self.info.get("dividendYield"),
            "roe": self.info.get("returnOnEquity"),
            "gross_margin": self.info.get("grossMargins"),
            "free_cash_flow": self.info.get("freeCashflow"),
            "held_percent_insiders": self.info.get("heldPercentInsiders"),
            "held_percent_institutions": self.info.get("heldPercentInstitutions"),
            "moat_rating": self.get_moat_analysis().get("rating"),
        }
