import math
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.valuation.wacc_calculator import WaccCalculator
from src.portfolio.portfolio_manager import PortfolioManager

console = Console()


class DcfValuation:
    """
    Modelo de Flujo de Caja Descontado (DCF / Discounted Cash Flow) en 2 etapas.
    Implementación fiel basada en la plantilla oficial 'DCF Simple.xlsx' de Fern Finance
    (Curso 'Análisis Fundamental - Hecho Simple').

    Fórmulas:
      1. Proyecciones a 5 Años:
         - Revenue(t) = Revenue(t-1) * (1 + RevenueGrowth(t))
         - OCF(t) = Revenue(t) * OCF_Margin
         - CapEx(t) = Revenue(t) * CapEx_Margin
         - FCF(t) = OCF(t) - CapEx(t)
         
      2. Valor Terminal (Gordon Growth / Perpetuidad al Año 5):
         - TV = (FCF(5) * (1 + g_perpetuo)) / (r - g_perpetuo)
         - g_perpetuo: Tasa de crecimiento a perpetuidad (default: 2.5%)
         - r: Tasa de descuento / RRR / WACC
         
      3. Descuento a Valor Presente (PV):
         - Para t = 1..4: PV(t) = FCF(t) / (1 + r)^t
         - Para t = 5:    PV(5) = (FCF(5) + TV) / (1 + r)^5
         
      4. Valor de la Empresa (Enterprise Value) y Valor Intrínseco por Acción:
         - EV = Sum(PV(t)) para t = 1..5
         - Equity Value = EV + Cash - Total Debt (o EV si puro)
         - Valor Intrínseco = Equity Value / Diluted Shares Outstanding
         - Margen de Seguridad = (Valor Intrínseco / Precio Actual) - 1
         - Señal: BUY si Margen > 0, SELL si Margen <= 0
    """

    DEFAULT_PERPETUAL_GROWTH = 0.025  # 2.5% anual a perpetuidad (PIB global / inflación)
    DEFAULT_DISCOUNT_RATE = 0.095     # 9.5% retorno requerido histórico del S&P 500

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        wacc_calc: Optional[WaccCalculator] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.wacc_calc = wacc_calc or WaccCalculator(extractor=self.extractor)
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def calculate_dcf(
        self,
        base_revenue: float,
        shares_diluted: float,
        current_price: float,
        revenue_growth_rates: List[float],
        ocf_margin: float,
        capex_margin: float,
        discount_rate: float = DEFAULT_DISCOUNT_RATE,
        perpetual_growth: float = DEFAULT_PERPETUAL_GROWTH,
        total_cash: float = 0.0,
        total_debt: float = 0.0,
        adjust_net_debt: bool = False,
    ) -> Dict[str, Any]:
        """
        Calcula el modelo DCF completo proyectando 5 años de FCF + Valor Terminal.
        """
        if len(revenue_growth_rates) < 5:
            # Rellenar con la última tasa si son menos de 5
            last_rate = revenue_growth_rates[-1] if revenue_growth_rates else 0.05
            revenue_growth_rates = list(revenue_growth_rates) + [last_rate] * (5 - len(revenue_growth_rates))
        else:
            revenue_growth_rates = revenue_growth_rates[:5]

        # Validar que tasa de descuento > crecimiento perpetuo
        r = max(discount_rate, perpetual_growth + 0.005)
        g = perpetual_growth

        # 1. Proyecciones anuales (Años 1 al 5)
        projections = []
        rev_prev = base_revenue
        pv_fcf_sum = 0.0

        for year in range(1, 6):
            g_rev = revenue_growth_rates[year - 1]
            rev_proj = rev_prev * (1.0 + g_rev)
            ocf_proj = rev_proj * ocf_margin
            capex_proj = rev_proj * capex_margin
            fcf_proj = ocf_proj - capex_proj
            
            discount_factor = (1.0 + r) ** year
            pv_fcf = fcf_proj / discount_factor
            pv_fcf_sum += pv_fcf

            projections.append({
                "year": year,
                "revenue": round(rev_proj, 2),
                "revenue_growth_pct": round(g_rev * 100, 2),
                "operating_cash_flow": round(ocf_proj, 2),
                "capex": round(capex_proj, 2),
                "free_cash_flow": round(fcf_proj, 2),
                "discount_factor": round(discount_factor, 4),
                "pv_fcf": round(pv_fcf, 2),
            })
            rev_prev = rev_proj

        fcf_year_5 = projections[-1]["free_cash_flow"]

        # 2. Valor Terminal (Gordon Growth al Año 5)
        terminal_value = (fcf_year_5 * (1.0 + g)) / (r - g)
        pv_terminal_value = terminal_value / ((1.0 + r) ** 5)

        # 3. Valor de la Empresa (Enterprise Value) y Equity Value
        enterprise_value = pv_fcf_sum + pv_terminal_value
        net_debt = total_debt - total_cash

        if adjust_net_debt:
            equity_value = enterprise_value - net_debt
        else:
            equity_value = enterprise_value

        # 4. Valor Intrínseco por Acción
        shares = max(1.0, shares_diluted)
        intrinsic_value = equity_value / shares

        # 5. Margen de Seguridad y Señal
        mos_pct = ((intrinsic_value / current_price) - 1.0) * 100 if current_price > 0 else 0.0
        diff = intrinsic_value - current_price
        signal = "BUY" if diff > 0 else "SELL"

        return {
            "intrinsic_value": round(intrinsic_value, 2),
            "current_price": round(current_price, 2),
            "difference": round(diff, 2),
            "margin_of_safety_pct": round(mos_pct, 2),
            "signal": signal,
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
            "terminal_value": round(terminal_value, 2),
            "pv_terminal_value": round(pv_terminal_value, 2),
            "pv_fcf_5yr_sum": round(pv_fcf_sum, 2),
            "terminal_value_weight_pct": round((pv_terminal_value / enterprise_value) * 100, 2) if enterprise_value > 0 else 0.0,
            "discount_rate_pct": round(r * 100, 2),
            "perpetual_growth_pct": round(g * 100, 2),
            "ocf_margin_pct": round(ocf_margin * 100, 2),
            "capex_margin_pct": round(capex_margin * 100, 2),
            "fcf_margin_pct": round((ocf_margin - capex_margin) * 100, 2),
            "shares_diluted": shares,
            "total_debt": total_debt,
            "total_cash": total_cash,
            "net_debt": net_debt,
            "adjust_net_debt": adjust_net_debt,
            "projections": projections,
        }

    def evaluate_ticker(
        self,
        ticker: str,
        custom_growth_rates: Optional[List[float]] = None,
        custom_discount_rate: Optional[float] = None,
        custom_perpetual_growth: Optional[float] = None,
        adjust_net_debt: bool = False,
    ) -> Dict[str, Any]:
        """
        Extrae la historia financiera de la SEC y calcula el DCF automáticamente.
        """
        # 1. Obtener historial SEC
        df = self.extractor.get_financial_history(ticker, period_type="annual")
        if df.empty:
            raise ValueError(f"No se pudieron obtener estados financieros SEC para {ticker}.")

        latest = df.iloc[-1]
        base_revenue = float(latest.get("revenue") or 0.0)
        shares_diluted = float(latest.get("shares_diluted") or latest.get("shares_basic") or 0.0)
        total_debt = float(latest.get("total_debt") or 0.0)
        total_cash = float(latest.get("cash") or 0.0)

        # 2. Calcular márgenes históricos promedio (últimos 3 a 5 años)
        hist_years = min(len(df), 5)
        recent_df = df.tail(hist_years)

        valid_rev = recent_df["revenue"].replace(0, np.nan)
        avg_ocf_margin = (recent_df["operating_cash_flow"] / valid_rev).mean()
        avg_capex_margin = (recent_df["capex"] / valid_rev).mean()

        if pd.isna(avg_ocf_margin) or avg_ocf_margin <= 0:
            avg_ocf_margin = 0.20  # Fallback a 20%
        if pd.isna(avg_capex_margin) or avg_capex_margin < 0:
            avg_capex_margin = 0.05  # Fallback a 5%

        # 3. Tasa de crecimiento promedio histórica de ingresos
        if custom_growth_rates:
            growth_rates = custom_growth_rates
        else:
            hist_growth = recent_df["revenue"].pct_change().dropna()
            avg_growth = hist_growth.mean() if not hist_growth.empty else 0.08
            # Desaceleración gradual a lo largo de 5 años (estándar de banca de inversión)
            clamped_g = max(0.02, min(avg_growth, 0.25))
            growth_rates = [
                clamped_g,
                clamped_g * 0.90,
                clamped_g * 0.80,
                clamped_g * 0.70,
                clamped_g * 0.60,
            ]

        # 4. Tasa de descuento (usar WACC calculado o 9.5% por defecto)
        if custom_discount_rate:
            discount_rate = custom_discount_rate
        else:
            try:
                wacc_res = self.wacc_calc.calculate_for_ticker(ticker)
                discount_rate = wacc_res["wacc"]
            except Exception:
                discount_rate = self.DEFAULT_DISCOUNT_RATE

        # 5. Precio actual
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
            except Exception:
                price = 100.0

        if shares_diluted <= 0:
            try:
                import yfinance as yf
                yt = yf.Ticker(ticker)
                mcap = float(getattr(yt.fast_info, "market_cap", 0.0) or 0.0)
                if mcap > 0 and price > 0:
                    shares_diluted = mcap / price
            except Exception:
                shares_diluted = 1_000_000_000

        res = self.calculate_dcf(
            base_revenue=base_revenue,
            shares_diluted=shares_diluted,
            current_price=price,
            revenue_growth_rates=growth_rates,
            ocf_margin=avg_ocf_margin,
            capex_margin=avg_capex_margin,
            discount_rate=discount_rate,
            perpetual_growth=custom_perpetual_growth or self.DEFAULT_PERPETUAL_GROWTH,
            total_cash=total_cash,
            total_debt=total_debt,
            adjust_net_debt=adjust_net_debt,
        )

        res["ticker"] = ticker.upper()
        res["company_name"] = self.extractor.get_company_name(ticker)
        res["base_year"] = str(df.index[-1])
        res["base_revenue"] = base_revenue
        return res

    def render_terminal_table(self, res: Dict[str, Any]):
        """Renderiza una tabla visual en consola con las proyecciones y el valor intrínseco del DCF."""
        ticker = res.get("ticker", "TICKER")
        comp = res.get("company_name", ticker)

        table = Table(
            title=f"[bold green]Modelo DCF (Discounted Cash Flow) - {ticker}[/bold green] ({comp})",
            header_style="bold magenta",
            border_style="green",
            expand=True
        )

        table.add_column("Métrica / Año", style="bold white", width=25)
        for proj in res["projections"]:
            table.add_column(f"Año {proj['year']} (E)", justify="right", style="cyan")

        # Fila Ingresos
        table.add_row(
            "Ingresos Proyectados ($M)",
            *[f"${p['revenue']/1e6:,.1f}" for p in res["projections"]]
        )
        # Fila Crecimiento %
        table.add_row(
            "Crecimiento Ingresos YoY",
            *[f"{p['revenue_growth_pct']:.1f}%" for p in res["projections"]]
        )
        # Fila Operating Cash Flow
        table.add_row(
            f"Operating Cash Flow ({res['ocf_margin_pct']:.1f}%)",
            *[f"${p['operating_cash_flow']/1e6:,.1f}" for p in res["projections"]]
        )
        # Fila CapEx
        table.add_row(
            f"CapEx ({res['capex_margin_pct']:.1f}%)",
            *[f"${p['capex']/1e6:,.1f}" for p in res["projections"]]
        )
        # Fila Free Cash Flow
        table.add_row(
            "[bold white]Free Cash Flow (FCF)[/bold white]",
            *[f"[bold yellow]${p['free_cash_flow']/1e6:,.1f}[/bold yellow]" for p in res["projections"]]
        )
        # Fila PV del FCF
        table.add_row(
            f"Valor Presente FCF (r={res['discount_rate_pct']}%)",
            *[f"${p['pv_fcf']/1e6:,.1f}" for p in res["projections"]]
        )

        console.print(table)

        # Tabla Resumen de Valuación
        summary_table = Table(
            title="[bold yellow]Resumen de Valuación e Intrinsic Value[/bold yellow]",
            header_style="bold cyan",
            border_style="yellow",
            expand=True
        )
        summary_table.add_column("Parámetro", style="bold white")
        summary_table.add_column("Valor", justify="right", style="green")
        summary_table.add_column("Notas", style="dim white")

        summary_table.add_row(
            "PV de Flujos 5 Años",
            f"${res['pv_fcf_5yr_sum']/1e6:,.1f} M",
            f"Suma de FCF descontados años 1 al 5"
        )
        summary_table.add_row(
            "Valor Terminal (Gordon Growth)",
            f"${res['terminal_value']/1e6:,.1f} M (PV: ${res['pv_terminal_value']/1e6:,.1f} M)",
            f"g={res['perpetual_growth_pct']}%, r={res['discount_rate_pct']}%, Peso: {res['terminal_value_weight_pct']}%"
        )
        summary_table.add_row(
            "Enterprise Value (EV)",
            f"${res['enterprise_value']/1e6:,.1f} M",
            "PV Flujos + PV Terminal"
        )
        summary_table.add_row(
            "Acciones Diluidas",
            f"{res['shares_diluted']/1e6:,.1f} M",
            "Weighted Average Diluted Shares (10-K)"
        )
        summary_table.add_row(
            "[bold white]VALOR INTRÍNSECO (Por Acción)[/bold white]",
            f"[bold cyan]${res['intrinsic_value']:.2f}[/bold cyan]",
            "[bold cyan]Equity Value / Acciones Diluidas[/bold cyan]"
        )
        summary_table.add_row(
            "Precio Actual de Mercado",
            f"${res['current_price']:.2f}",
            "Último precio cotizado"
        )
        
        mos_style = "bold green" if res["margin_of_safety_pct"] > 0 else "bold red"
        signal_style = "bold green on black" if res["signal"] == "BUY" else "bold red on black"
        
        summary_table.add_row(
            "Margen de Seguridad %",
            f"[{mos_style}]{res['margin_of_safety_pct']:+.1f}%[/{mos_style}]",
            f"Diferencia: ${res['difference']:+.2f}"
        )
        summary_table.add_row(
            "[bold white]SEÑAL DEL MODELO[/bold white]",
            f"[{signal_style}] {res['signal']} [/{signal_style}]",
            "BUY si Precio < Valor Intrínseco"
        )

        console.print(summary_table)
