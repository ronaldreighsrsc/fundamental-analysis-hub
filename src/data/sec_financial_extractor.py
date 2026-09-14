import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.data.sec_edgar_downloader import SecEdgarDownloader


class SecFinancialExtractor:
    """
    Extrae, limpia y normaliza series temporales financieras multianuales (10 a 17+ anios)
    directamente desde los informes 10-K y 10-Q de la SEC en formato XBRL/US-GAAP.
    Combina etiquetas contables previas y posteriores a la norma ASC 606 (2018) para garantizar
    series historicas completas sin interrupciones.
    """

    GAAP_CONCEPTS = {
        "revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "HealthCareOrganizationPatientServiceRevenue",
            "HealthCareOrganizationRevenue",
        ],
        "cost_of_revenue": [
            "CostOfGoodsAndServicesSold",
            "CostOfRevenue",
            "CostOfServices",
        ],
        "gross_profit": [
            "GrossProfit",
        ],
        "operating_income": [
            "OperatingIncomeLoss",
        ],
        "net_income": [
            "NetIncomeLoss",
            "ProfitLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic",
        ],
        "operating_cash_flow": [
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        "capex": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
            "PaymentsForPropertyPlantAndEquipment",
        ],
        "shares_diluted": [
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingDiluted",
            "CommonStockSharesOutstanding",
        ],
        "eps_diluted": [
            "EarningsPerShareDiluted",
        ],
        "total_assets": [
            "Assets",
        ],
        "total_debt": [
            "LongTermDebtNoncurrent",
            "LongTermDebtAndCapitalLeaseObligations",
            "LongTermDebt",
        ],
        "cash": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ],
        "stockholders_equity": [
            "StockholdersEquity",
            "CommonStockholdersEquity",
        ],
    }

    def __init__(self, downloader: Optional[SecEdgarDownloader] = None):
        self.downloader = downloader or SecEdgarDownloader()

    def _extract_fact_series(
        self, facts: Dict[str, Any], concept_keys: List[str], period_type: str = "annual"
    ) -> Dict[str, float]:
        """
        Extrae la serie temporal para un concepto contable.
        Itera por todas las etiquetas candidatas para rellenar periodos historicos
        (por ejemplo, transicion pre y post ASC 606 en 2018).
        """
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        entries_by_period = {}

        for tag in concept_keys:
            if tag not in us_gaap:
                continue

            concept_data = us_gaap[tag]
            units_data = concept_data.get("units", {})
            unit_entries = units_data.get("USD") or units_data.get("shares") or []

            for item in unit_entries:
                form = item.get("form", "")
                val = item.get("val")
                if val is None:
                    continue

                filed_date = item.get("filed", "")
                start_str = item.get("start")
                end_str = item.get("end")

                if period_type == "annual":
                    # Filtro para 10-K anuales
                    if form not in ("10-K", "10-K/A"):
                        continue

                    period_key = None
                    if start_str and end_str:
                        try:
                            start = datetime.strptime(start_str, "%Y-%m-%d")
                            end = datetime.strptime(end_str, "%Y-%m-%d")
                            days = (end - start).days
                            # Periodo anual (~330 a 390 dias)
                            if 330 <= days <= 390:
                                fy = item.get("fy") or end.year
                                period_key = str(fy)
                        except Exception:
                            pass
                    elif end_str:
                        # Items instantaneos (balance sheet)
                        fy = item.get("fy")
                        if fy:
                            period_key = str(fy)
                        else:
                            period_key = end_str[:4]

                    if period_key:
                        # Si ya existe para este periodo, conservar el filing mas reciente
                        existing = entries_by_period.get(period_key)
                        if not existing or filed_date > existing["filed"]:
                            entries_by_period[period_key] = {"val": float(val), "filed": filed_date}

                elif period_type == "quarterly":
                    # Filtro para 10-Q trimestrales
                    if form not in ("10-Q", "10-Q/A"):
                        continue

                    fp = item.get("fp", "")
                    fy = item.get("fy")
                    if fy and fp in ("Q1", "Q2", "Q3"):
                        period_key = f"{fy}-{fp}"
                        existing = entries_by_period.get(period_key)
                        if not existing or filed_date > existing["filed"]:
                            entries_by_period[period_key] = {"val": float(val), "filed": filed_date}

        return {k: v["val"] for k, v in entries_by_period.items()}

    def get_financial_history(
        self, ticker: str, period_type: str = "annual", force: bool = False
    ) -> pd.DataFrame:
        """
        Descarga y procesa la historia financiera completa (10 a 17+ anios) de un ticker.
        Retorna un DataFrame de Pandas indexado cronologicamente por periodo.
        """
        facts = self.downloader.fetch_company_facts(ticker, force=force)
        raw_series = {}

        for concept_name, tags in self.GAAP_CONCEPTS.items():
            s = self._extract_fact_series(facts, tags, period_type=period_type)
            if s:
                raw_series[concept_name] = s

        if not raw_series:
            return pd.DataFrame()

        df = pd.DataFrame(raw_series)
        if df.empty:
            return df

        # Ordenar cronologicamente por el indice
        df = df.sort_index()

        # Rellenar o estimar Gross Profit si falta (Ventas - Costo de Ventas)
        if "gross_profit" not in df.columns or df["gross_profit"].isnull().all():
            if "revenue" in df.columns and "cost_of_revenue" in df.columns:
                df["gross_profit"] = df["revenue"] - df["cost_of_revenue"]

        # Calcular Flujo de Caja Libre (FCF = Operating Cash Flow - CapEx)
        if "operating_cash_flow" in df.columns:
            capex = df.get("capex", pd.Series(0, index=df.index)).fillna(0)
            df["free_cash_flow"] = df["operating_cash_flow"] - capex

        # Calculo de Margenes Porcentuales
        if "revenue" in df.columns:
            rev = df["revenue"].replace(0, np.nan)
            if "gross_profit" in df.columns:
                df["gross_margin_pct"] = (df["gross_profit"] / rev) * 100
            if "operating_income" in df.columns:
                df["operating_margin_pct"] = (df["operating_income"] / rev) * 100
            if "net_income" in df.columns:
                df["net_margin_pct"] = (df["net_income"] / rev) * 100
            if "free_cash_flow" in df.columns:
                df["fcf_margin_pct"] = (df["free_cash_flow"] / rev) * 100

        # Crecimiento Interanual (YoY %)
        if "revenue" in df.columns:
            df["revenue_growth_yoy"] = df["revenue"].pct_change() * 100
        if "net_income" in df.columns:
            df["net_income_growth_yoy"] = df["net_income"].pct_change() * 100
        if "free_cash_flow" in df.columns:
            df["fcf_growth_yoy"] = df["free_cash_flow"].pct_change() * 100
        if "shares_diluted" in df.columns:
            df["shares_change_yoy"] = df["shares_diluted"].pct_change() * 100

        # Intensidad de Capital (CapEx / Operating Cash Flow %)
        if "capex" in df.columns and "operating_cash_flow" in df.columns:
            ocf = df["operating_cash_flow"].replace(0, np.nan)
            df["capex_to_ocf_pct"] = (df["capex"] / ocf) * 100

        return df

    def get_company_name(self, ticker: str) -> str:
        """Obtiene el nombre oficial de la empresa registrado en la SEC."""
        try:
            facts = self.downloader.fetch_company_facts(ticker)
            return facts.get("entityName") or ticker.upper()
        except Exception:
            return ticker.upper()
