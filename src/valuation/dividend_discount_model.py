import math
from typing import Dict, Any, List, Optional
import pandas as pd
from rich.console import Console
from rich.table import Table

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.valuation.wacc_calculator import WaccCalculator
from src.portfolio.portfolio_manager import PortfolioManager

console = Console()


class DividendDiscountModel:
    """
    Modelo de Descuento de Dividendos (DDM / Dividend Discount Model - Gordon Growth).
    Implementación fiel basada en la plantilla oficial 'Dividend Disctount Model.xlsx'
    de Fern Finance (Curso 'Análisis Fundamental - Hecho Simple').

    Fórmulas:
      1. Tasa de Crecimiento de Dividendos (g):
         - Historial de dividendos por acción anuales (D0, D-1, D-2, D-3).
         - Promedio de crecimiento interanual o CAGR histórico.
         
      2. Tasa de Retorno Requerido (r):
         - RRR / Costo del Equity (Ke) obtenido vía CAPM / WACC.
         
      3. Valor Intrínseco (Gordon Growth):
         - IV = (D0 * (1 + g)) / (r - g) = D1 / (r - g)
         - Condición matemática: r > g.
         
      4. Señal y Margen de Seguridad:
         - Margen de Seguridad = (IV / PrecioActual) - 1
         - Señal: BUY si IV > PrecioActual, SELL en caso contrario.
    """

    DEFAULT_RRR = 0.095       # 9.5% retorno mínimo requerido por defecto
    DEFAULT_DIV_GROWTH = 0.05 # 5.0% crecimiento anual estimado

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        wacc_calc: Optional[WaccCalculator] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.wacc_calc = wacc_calc or WaccCalculator(extractor=self.extractor)
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def calculate_ddm(
        self,
        annual_dividend: float,
        current_price: float,
        dividend_growth_rate: float = DEFAULT_DIV_GROWTH,
        required_return: float = DEFAULT_RRR,
    ) -> Dict[str, Any]:
        """
        Calcula el valor intrínseco Gordon Growth a partir del dividendo actual,
        la tasa de crecimiento esperada y el retorno requerido.
        """
        if annual_dividend <= 0:
            return {
                "intrinsic_value": 0.0,
                "current_price": round(current_price, 2),
                "annual_dividend": 0.0,
                "dividend_yield_pct": 0.0,
                "dividend_growth_rate_pct": round(dividend_growth_rate * 100, 2),
                "required_return_pct": round(required_return * 100, 2),
                "difference": round(-current_price, 2),
                "margin_of_safety_pct": -100.0,
                "signal": "NO PAGA DIVIDENDOS",
            }

        r = required_return
        g = dividend_growth_rate

        if r <= g:
            # Si el crecimiento supera el retorno requerido, Gordon Growth diverge
            # Se aplica un ajuste conservador donde g = r - 0.015
            g = max(0.01, r - 0.015)

        next_dividend = annual_dividend * (1.0 + g)
        intrinsic_value = next_dividend / (r - g)

        diff = intrinsic_value - current_price
        mos_pct = ((intrinsic_value / current_price) - 1.0) * 100 if current_price > 0 else 0.0
        signal = "BUY" if diff > 0 else "SELL"
        div_yield = (annual_dividend / current_price) * 100 if current_price > 0 else 0.0

        return {
            "intrinsic_value": round(intrinsic_value, 2),
            "current_price": round(current_price, 2),
            "annual_dividend": round(annual_dividend, 2),
            "next_dividend": round(next_dividend, 2),
            "dividend_yield_pct": round(div_yield, 2),
            "dividend_growth_rate_pct": round(g * 100, 2),
            "required_return_pct": round(r * 100, 2),
            "difference": round(diff, 2),
            "margin_of_safety_pct": round(mos_pct, 2),
            "signal": signal,
        }

    def evaluate_ticker(
        self,
        ticker: str,
        custom_dividend_growth: Optional[float] = None,
        custom_required_return: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extrae automáticamente el dividendo anual y precio del ticker para calcular el DDM.
        """
        info = {}
        try:
            profile = self.portfolio_mgr.get_company_profile(ticker)
            if profile and "info" in profile:
                info = profile["info"]
        except Exception:
            pass

        price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
        annual_div = float(info.get("dividendRate") or 0.0)

        # Fallback a yfinance
        if price <= 0 or annual_div <= 0:
            try:
                import yfinance as yf
                yt = yf.Ticker(ticker)
                if price <= 0:
                    price = float(getattr(yt.fast_info, "last_price", 0.0) or 0.0)
                if annual_div <= 0:
                    yinfo = getattr(yt, "info", {})
                    annual_div = float(yinfo.get("dividendRate") or 0.0)
                    if annual_div <= 0 and "dividendYield" in yinfo and price > 0:
                        annual_div = price * float(yinfo["dividendYield"])
            except Exception:
                pass

        # Retorno requerido (Costo del Equity / Ke o 9.5%)
        if custom_required_return:
            rrr = custom_required_return
        else:
            try:
                wacc_res = self.wacc_calc.calculate_for_ticker(ticker)
                rrr = wacc_res["cost_of_equity"]
            except Exception:
                rrr = self.DEFAULT_RRR

        growth_rate = custom_dividend_growth or self.DEFAULT_DIV_GROWTH

        res = self.calculate_ddm(
            annual_dividend=annual_div,
            current_price=price,
            dividend_growth_rate=growth_rate,
            required_return=rrr,
        )

        res["ticker"] = ticker.upper()
        res["company_name"] = self.extractor.get_company_name(ticker)
        return res

    def render_terminal_table(self, res: Dict[str, Any]):
        """Renderiza una tabla visual en consola con la valuación por Gordon Growth."""
        ticker = res.get("ticker", "TICKER")
        comp = res.get("company_name", ticker)

        table = Table(
            title=f"[bold green]Modelo DDM (Dividend Discount Model) - {ticker}[/bold green] ({comp})",
            header_style="bold magenta",
            border_style="green",
            expand=True
        )

        table.add_column("Concepto", style="bold white", width=32)
        table.add_column("Valor", justify="right", style="cyan", width=20)
        table.add_column("Detalle / Fórmula", style="dim white")

        table.add_row(
            "Dividendo Anual Actual (D0)",
            f"${res['annual_dividend']:.2f}",
            f"Dividend Yield: {res['dividend_yield_pct']}%"
        )
        table.add_row(
            "Dividendo Esperado Próximo Año (D1)",
            f"${res.get('next_dividend', res['annual_dividend']):.2f}",
            f"D0 * (1 + g={res['dividend_growth_rate_pct']}%)"
        )
        table.add_row(
            "Tasa de Retorno Requerida (r / RRR)",
            f"{res['required_return_pct']:.2f}%",
            "Costo del Equity (CAPM) / Tasa de descuento"
        )
        table.add_row(
            "Tasa de Crecimiento Dividendos (g)",
            f"{res['dividend_growth_rate_pct']:.2f}%",
            "Crecimiento anual a perpetuidad"
        )
        table.add_row(
            "[bold white]VALOR INTRÍNSECO (DDM)[/bold white]",
            f"[bold cyan]${res['intrinsic_value']:.2f}[/bold cyan]",
            "[bold yellow]D1 / (r - g)[/bold yellow]"
        )
        table.add_row(
            "Precio Actual de Mercado",
            f"${res['current_price']:.2f}",
            "Cotización en tiempo real"
        )

        mos_style = "bold green" if res["margin_of_safety_pct"] > 0 else "bold red"
        signal_style = "bold green on black" if res["signal"] == "BUY" else "bold red on black"

        table.add_row(
            "Margen de Seguridad %",
            f"[{mos_style}]{res['margin_of_safety_pct']:+.1f}%[/{mos_style}]",
            f"Diferencia: ${res['difference']:+.2f}"
        )
        table.add_row(
            "[bold white]SEÑAL DEL MODELO[/bold white]",
            f"[{signal_style}] {res['signal']} [/{signal_style}]",
            "BUY si Precio < Valor Intrínseco"
        )

        console.print(table)
