import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.valuation.wacc_calculator import WaccCalculator
from src.valuation.dcf_valuation import DcfValuation
from src.portfolio.portfolio_manager import PortfolioManager

console = Console()


class ReverseDcfValuation:
    """
    Modelo de Valuación Inversa (Reverse DCF / Implied Growth).
    Implementación basada en la lección oficial 'Valuación Inversa' de Fern Finance
    (Curso 'Análisis Fundamental - Hecho Simple').

    Filosofía del modelo:
      En lugar de adivinar qué crecimiento tendrá la empresa, la valuación inversa
      resuelve algebraicamente la pregunta clave del inversor inteligente:
      
      '¿Qué tasa de crecimiento anual de Flujo de Caja Libre (FCF) está descontando
       el mercado en el precio actual de la acción?'

      Si el mercado exige un crecimiento del 25% anual y la empresa históricamente
      crece al 10%, el riesgo de decepción es enorme (Expectation Treadmill).
      Si el mercado solo exige un 4% y la empresa crece al 12%, existe una gran
      asimetría positiva a favor del inversor.
    """

    DEFAULT_PERPETUAL_GROWTH = 0.025  # 2.5%
    DEFAULT_DISCOUNT_RATE = 0.095     # 9.5%

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        wacc_calc: Optional[WaccCalculator] = None,
        dcf_model: Optional[DcfValuation] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.wacc_calc = wacc_calc or WaccCalculator(extractor=self.extractor)
        self.dcf_model = dcf_model or DcfValuation(extractor=self.extractor, wacc_calc=self.wacc_calc)
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def find_implied_growth(
        self,
        base_fcf: float,
        shares_diluted: float,
        current_price: float,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        perpetual_growth: float = DEFAULT_PERPETUAL_GROWTH,
        years: int = 5,
    ) -> Dict[str, Any]:
        """
        Calcula mediante bisección numérica la tasa de crecimiento anual de FCF
        que iguala exactamente el Valor Intrínseco al Precio Actual.
        """
        if base_fcf <= 0 or current_price <= 0 or shares_diluted <= 0:
            return {
                "implied_growth_pct": 0.0,
                "status": "ERROR_INPUTS",
                "message": "FCF, Precio o Acciones deben ser positivos para Valuación Inversa."
            }

        target_equity_value = current_price * shares_diluted
        r = discount_rate
        g_term = perpetual_growth

        def equity_value_at_growth(g: float) -> float:
            # Proyección simple de FCF constante a tasa g
            pv_sum = 0.0
            fcf = base_fcf
            for y in range(1, years + 1):
                fcf *= (1.0 + g)
                pv_sum += fcf / ((1.0 + r) ** y)
            
            # Terminal Value
            tv = (fcf * (1.0 + g_term)) / (r - g_term)
            pv_tv = tv / ((1.0 + r) ** years)
            return pv_sum + pv_tv

        # Bisección entre -30% y +60% anual
        low = -0.30
        high = 0.60
        implied_g = 0.0

        for _ in range(60):
            mid = (low + high) / 2.0
            val = equity_value_at_growth(mid)
            if abs(val - target_equity_value) < 1000:
                implied_g = mid
                break
            if val < target_equity_value:
                low = mid
            else:
                high = mid
            implied_g = mid

        return {
            "implied_growth": round(implied_g, 4),
            "implied_growth_pct": round(implied_g * 100, 2),
            "current_price": round(current_price, 2),
            "base_fcf": round(base_fcf, 2),
            "shares_diluted": shares_diluted,
            "discount_rate_pct": round(r * 100, 2),
            "perpetual_growth_pct": round(g_term * 100, 2),
            "target_equity_value": round(target_equity_value, 2),
        }

    def evaluate_ticker(
        self,
        ticker: str,
        custom_discount_rate: Optional[float] = None,
        custom_perpetual_growth: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extrae datos históricos de la SEC y calcula el crecimiento implícito por el mercado.
        """
        df = self.extractor.get_financial_history(ticker, period_type="annual")
        if df.empty:
            raise ValueError(f"No se pudieron obtener estados financieros SEC para {ticker}.")

        latest = df.iloc[-1]
        base_fcf = float(latest.get("free_cash_flow") or 0.0)
        shares_diluted = float(latest.get("shares_diluted") or latest.get("shares_basic") or 0.0)

        # Si el FCF del último año fue anormal, usar el promedio de los últimos 3 años
        if base_fcf <= 0 and "free_cash_flow" in df.columns:
            base_fcf = float(df["free_cash_flow"].tail(3).mean())

        # Precio actual
        price = 0.0
        try:
            profile = self.portfolio_mgr.get_company_profile(ticker)
            if profile and "info" in profile:
                price = float(profile["info"].get("currentPrice") or profile["info"].get("regularMarketPrice") or 0.0)
        except Exception:
            pass

        if price <= 0:
            try:
                import yfinance as yf
                yt = yf.Ticker(ticker)
                price = float(getattr(yt.fast_info, "last_price", 0.0) or 0.0)
                if shares_diluted <= 0:
                    mcap = float(getattr(yt.fast_info, "market_cap", 0.0) or 0.0)
                    if mcap > 0 and price > 0:
                        shares_diluted = mcap / price
            except Exception:
                price = 100.0

        if custom_discount_rate:
            r = custom_discount_rate
        else:
            try:
                wacc_res = self.wacc_calc.calculate_for_ticker(ticker)
                r = wacc_res["wacc"]
            except Exception:
                r = self.DEFAULT_DISCOUNT_RATE

        res = self.find_implied_growth(
            base_fcf=base_fcf,
            shares_diluted=shares_diluted,
            current_price=price,
            discount_rate=r,
            perpetual_growth=custom_perpetual_growth or self.DEFAULT_PERPETUAL_GROWTH,
        )

        # Comparativa con crecimiento histórico real
        hist_years = min(len(df), 5)
        recent_df = df.tail(hist_years)
        hist_fcf_growth = 0.0
        if "free_cash_flow" in recent_df.columns:
            fcf_s = recent_df["free_cash_flow"].dropna()
            if len(fcf_s) >= 2 and fcf_s.iloc[0] > 0 and fcf_s.iloc[-1] > 0:
                hist_fcf_growth = float(((fcf_s.iloc[-1] / fcf_s.iloc[0]) ** (1.0 / (len(fcf_s) - 1)) - 1.0) * 100)

        res["ticker"] = ticker.upper()
        res["company_name"] = self.extractor.get_company_name(ticker)
        res["historical_fcf_cagr_pct"] = round(hist_fcf_growth, 2)
        
        # Evaluación de asimetría / veredicto
        implied_g = res["implied_growth_pct"]
        if implied_g > hist_fcf_growth + 8.0:
            verdict = "ALTO RIESGO DE EXPECTATIVAS"
            verdict_desc = f"El mercado descuenta {implied_g:.1f}% anual, muy por encima de su historial ({hist_fcf_growth:.1f}%)."
            verdict_color = "bold red"
        elif implied_g < hist_fcf_growth - 5.0:
            verdict = "OPORTUNIDAD ASIMÉTRICA (BAJAS EXPECTATIVAS)"
            verdict_desc = f"El mercado solo descuenta {implied_g:.1f}% anual, inferior a su historial ({hist_fcf_growth:.1f}%)."
            verdict_color = "bold green"
        else:
            verdict = "VALORACIÓN EQUILIBRADA"
            verdict_desc = f"El crecimiento implícito ({implied_g:.1f}%) está alineado con su historial ({hist_fcf_growth:.1f}%)."
            verdict_color = "bold yellow"

        res["verdict"] = verdict
        res["verdict_desc"] = verdict_desc
        res["verdict_color"] = verdict_color
        return res

    def render_terminal_table(self, res: Dict[str, Any]):
        """Renderiza una tabla visual en consola con el análisis de Valuación Inversa."""
        ticker = res.get("ticker", "TICKER")
        comp = res.get("company_name", ticker)

        table = Table(
            title=f"[bold yellow]Modelo de Valuación Inversa (Reverse DCF) - {ticker}[/bold yellow] ({comp})",
            header_style="bold magenta",
            border_style="yellow",
            expand=True
        )

        table.add_column("Métrica", style="bold white", width=34)
        table.add_column("Valor", justify="right", style="cyan", width=20)
        table.add_column("Interpretación", style="dim white")

        table.add_row(
            "Precio Actual de Mercado",
            f"${res['current_price']:.2f}",
            "Punto de partida del mercado"
        )
        table.add_row(
            "Free Cash Flow Base (10-K)",
            f"${res['base_fcf']/1e6:,.1f} M",
            "Último año fiscal SEC"
        )
        table.add_row(
            "Tasa de Descuento (WACC / r)",
            f"{res['discount_rate_pct']:.2f}%",
            "Retorno anual exigido"
        )
        table.add_row(
            "[bold white]CRECIMIENTO IMPLÍCITO FCF (5 Años)[/bold white]",
            f"[bold yellow]{res['implied_growth_pct']:+.1f}% anual[/bold yellow]",
            "[bold white]Crecimiento que el precio actual exige[/bold white]"
        )
        table.add_row(
            "Crecimiento FCF Histórico Real",
            f"{res.get('historical_fcf_cagr_pct', 0.0):+.1f}% anual",
            "CAGR de FCF últimos 3 a 5 años"
        )

        color = res.get("verdict_color", "bold cyan")
        table.add_row(
            "[bold white]VEREDICTO DE EXPECTATIVAS[/bold white]",
            f"[{color}]{res.get('verdict', 'NEUTRAL')}[/{color}]",
            f"[{color}]{res.get('verdict_desc', '')}[/{color}]"
        )

        console.print(table)
