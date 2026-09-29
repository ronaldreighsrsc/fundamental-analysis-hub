import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.portfolio.portfolio_manager import PortfolioManager

console = Console()


class PeForwardValuation:
    """
    Modelo de Valuación por Múltiplos P/E a 5 Años con modelado explícito de
    Recompra de Acciones (Buybacks) o Dilución (SBC / Stock-Based Compensation).
    Implementación fiel basada en la plantilla oficial 'Modelo De Valuacion (P:E).xlsx'
    de Fern Finance (Curso 'Análisis Fundamental - Hecho Simple').

    Fórmulas:
      1. Proyección de Ventas y Beneficios:
         - Ventas(t) = Ventas(t-1) * (1 + Crecimiento(t))
         - Beneficio Neto(t) = Ventas(t) * Margen Neto
         
      2. Evolución de Acciones (El factor crítico del curso):
         - Acciones(t) = Acciones(t-1) * (1 + TasaDilucion)
         - TasaDilucion negativa (-2.5%) = Recompras netas (Buybacks)
         - TasaDilucion positiva (+3.0%) = Dilución por opciones / RSUs
         
      3. Beneficio por Acción (Forward EPS):
         - Forward EPS(t) = Beneficio Neto(t) / Acciones(t)
         
      4. Precio Objetivo en 5 Años:
         - PrecioObjetivo(5) = PE_Esperado(5) * Forward_EPS(5)
         - Retorno Total % = (PrecioObjetivo(5) / PrecioActual) - 1
         - Retorno Anualizado (CAGR) = (1 + RetornoTotal)^(1/5) - 1
         - Señal: COMPRAR si Retorno Total > 0, VENDER si <= 0
    """

    DEFAULT_TARGET_PE = 20.0
    DEFAULT_HURDLE_CAGR = 0.10  # 10% CAGR mínimo exigido

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def calculate_model(
        self,
        base_revenue: float,
        base_shares: float,
        current_price: float,
        net_margin: float,
        revenue_growth_rates: List[float],
        dilution_or_buyback_rate: float,
        target_pe_5yr: float = DEFAULT_TARGET_PE,
    ) -> Dict[str, Any]:
        """
        Calcula la evolución de ingresos, acciones, EPS y retorno proyectado a 5 años.
        """
        if len(revenue_growth_rates) < 5:
            last_rate = revenue_growth_rates[-1] if revenue_growth_rates else 0.06
            revenue_growth_rates = list(revenue_growth_rates) + [last_rate] * (5 - len(revenue_growth_rates))
        else:
            revenue_growth_rates = revenue_growth_rates[:5]

        projections = []
        rev_prev = base_revenue
        shares_prev = base_shares

        for year in range(1, 6):
            g_rev = revenue_growth_rates[year - 1]
            rev_proj = rev_prev * (1.0 + g_rev)
            net_income_proj = rev_proj * net_margin
            
            # Ajuste de acciones por buyback o dilucion
            shares_proj = shares_prev * (1.0 + dilution_or_buyback_rate)
            fwd_eps = net_income_proj / max(1.0, shares_proj)
            fwd_pe = current_price / fwd_eps if fwd_eps > 0 else 0.0

            projections.append({
                "year": year,
                "revenue": round(rev_proj, 2),
                "revenue_growth_pct": round(g_rev * 100, 2),
                "net_income": round(net_income_proj, 2),
                "shares_outstanding": round(shares_proj, 2),
                "shares_change_pct": round(dilution_or_buyback_rate * 100, 2),
                "forward_eps": round(fwd_eps, 4),
                "forward_pe": round(fwd_pe, 2),
            })
            rev_prev = rev_proj
            shares_prev = shares_proj

        final_eps = projections[-1]["forward_eps"]
        expected_price_5yr = target_pe_5yr * final_eps

        total_return_pct = ((expected_price_5yr / current_price) - 1.0) * 100 if current_price > 0 else 0.0
        
        # CAGR retorno compuesto
        if current_price > 0 and expected_price_5yr > 0:
            cagr = ((expected_price_5yr / current_price) ** (1.0 / 5.0) - 1.0) * 100
        else:
            cagr = -100.0

        signal = "COMPRAR" if total_return_pct > 0 else "VENDER"

        return {
            "current_price": round(current_price, 2),
            "expected_price_5yr": round(expected_price_5yr, 2),
            "total_return_pct": round(total_return_pct, 2),
            "annualized_cagr_pct": round(cagr, 2),
            "signal": signal,
            "target_pe_5yr": round(target_pe_5yr, 2),
            "final_forward_eps": round(final_eps, 2),
            "net_margin_pct": round(net_margin * 100, 2),
            "dilution_or_buyback_rate_pct": round(dilution_or_buyback_rate * 100, 2),
            "base_shares": base_shares,
            "final_shares": projections[-1]["shares_outstanding"],
            "shares_total_change_pct": round(((projections[-1]["shares_outstanding"] / base_shares) - 1.0) * 100, 2) if base_shares > 0 else 0.0,
            "projections": projections,
        }

    def evaluate_ticker(
        self,
        ticker: str,
        custom_growth_rates: Optional[List[float]] = None,
        custom_target_pe: Optional[float] = None,
        custom_dilution_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extrae datos históricos de la SEC para auto-completar margen neto,
        tasa histórica de buybacks/dilución y ventas base.
        """
        df = self.extractor.get_financial_history(ticker, period_type="annual")
        if df.empty:
            raise ValueError(f"No se pudieron obtener estados financieros SEC para {ticker}.")

        latest = df.iloc[-1]
        base_revenue = float(latest.get("revenue") or 0.0)
        base_shares = float(latest.get("shares_diluted") or latest.get("shares_basic") or 0.0)

        # 1. Margen neto promedio de los últimos 3-5 años
        hist_years = min(len(df), 5)
        recent_df = df.tail(hist_years)
        valid_rev = recent_df["revenue"].replace(0, np.nan)
        avg_net_margin = (recent_df["net_income"] / valid_rev).mean()
        if pd.isna(avg_net_margin) or avg_net_margin <= 0:
            avg_net_margin = 0.15

        # 2. Tasa histórica de buyback o dilución de acciones (en ventana reciente post-splits)
        if custom_dilution_rate is not None:
            dilution_rate = custom_dilution_rate
        else:
            if "shares_diluted" in recent_df.columns:
                shares_s = recent_df["shares_diluted"].dropna()
                if len(shares_s) >= 2:
                    # CAGR histórico de acciones de los últimos años
                    n_years = len(shares_s) - 1
                    shares_cagr = (shares_s.iloc[-1] / shares_s.iloc[0]) ** (1.0 / n_years) - 1.0
                    dilution_rate = float(shares_cagr)
                else:
                    dilution_rate = -0.015  # -1.5% promedio de recompras
            else:
                dilution_rate = 0.0

        # Clamping de seguridad para la tasa de dilución (-5% a +5% anual)
        dilution_rate = max(-0.06, min(dilution_rate, 0.06))

        # 3. Crecimiento de ingresos
        if custom_growth_rates:
            growth_rates = custom_growth_rates
        else:
            hist_growth = recent_df["revenue"].pct_change().dropna()
            avg_growth = hist_growth.mean() if not hist_growth.empty else 0.08
            clamped_g = max(0.02, min(avg_growth, 0.25))
            growth_rates = [clamped_g, clamped_g * 0.9, clamped_g * 0.8, clamped_g * 0.7, clamped_g * 0.6]

        # 4. Precio actual
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

        target_pe = custom_target_pe or self.DEFAULT_TARGET_PE

        res = self.calculate_model(
            base_revenue=base_revenue,
            base_shares=base_shares,
            current_price=price,
            net_margin=avg_net_margin,
            revenue_growth_rates=growth_rates,
            dilution_or_buyback_rate=dilution_rate,
            target_pe_5yr=target_pe,
        )

        res["ticker"] = ticker.upper()
        res["company_name"] = self.extractor.get_company_name(ticker)
        res["base_year"] = str(df.index[-1])
        return res

    def render_terminal_table(self, res: Dict[str, Any]):
        """Renderiza una tabla visual en consola con la evolución forward y retornos esperados."""
        ticker = res.get("ticker", "TICKER")
        comp = res.get("company_name", ticker)

        table = Table(
            title=f"[bold cyan]Modelo P/E Multiple Forward (5 Años) - {ticker}[/bold cyan] ({comp})",
            header_style="bold magenta",
            border_style="cyan",
            expand=True
        )

        table.add_column("Métrica / Año", style="bold white", width=28)
        for proj in res["projections"]:
            table.add_column(f"Año {proj['year']} (E)", justify="right", style="cyan")

        table.add_row(
            "Ventas Proyectadas ($M)",
            *[f"${p['revenue']/1e6:,.1f}" for p in res["projections"]]
        )
        table.add_row(
            "Crecimiento Ventas YoY",
            *[f"{p['revenue_growth_pct']:.1f}%" for p in res["projections"]]
        )
        table.add_row(
            f"Beneficio Neto ({res['net_margin_pct']:.1f}%)",
            *[f"${p['net_income']/1e6:,.1f}" for p in res["projections"]]
        )
        
        dil_label = "Recompras (Buybacks)" if res["dilution_or_buyback_rate_pct"] < 0 else "Dilución Acciones"
        table.add_row(
            f"Acciones Diluidas ({dil_label})",
            *[f"{p['shares_outstanding']/1e6:,.1f} M" for p in res["projections"]]
        )
        table.add_row(
            "[bold white]Forward EPS ($)[/bold white]",
            *[f"[bold yellow]${p['forward_eps']:.2f}[/bold yellow]" for p in res["projections"]]
        )
        table.add_row(
            f"Forward P/E (al precio actual)",
            *[f"{p['forward_pe']:.1f}x" for p in res["projections"]]
        )

        console.print(table)

        # Tabla Resumen de Retorno
        summary_table = Table(
            title="[bold yellow]Retorno Esperado y Señal de Inversión[/bold yellow]",
            header_style="bold green",
            border_style="yellow",
            expand=True
        )
        summary_table.add_column("Concepto", style="bold white")
        summary_table.add_column("Valor", justify="right", style="green")
        summary_table.add_column("Detalle", style="dim white")

        summary_table.add_row(
            "Precio Actual de la Acción",
            f"${res['current_price']:.2f}",
            "Cotización en tiempo real"
        )
        summary_table.add_row(
            "P/E Múltiplo Esperado (Año 5)",
            f"{res['target_pe_5yr']:.1f}x",
            "Múltiplo de salida terminal"
        )
        summary_table.add_row(
            "Forward EPS en Año 5",
            f"${res['final_forward_eps']:.2f}",
            "Beneficio neto / acciones tras buybacks/dilución"
        )
        summary_table.add_row(
            "[bold white]Precio Objetivo en 5 Años[/bold white]",
            f"[bold cyan]${res['expected_price_5yr']:.2f}[/bold cyan]",
            "P/E Terminal * Forward EPS (Año 5)"
        )
        
        ret_style = "bold green" if res["total_return_pct"] > 0 else "bold red"
        summary_table.add_row(
            "Retorno Total Esperado (5 Años)",
            f"[{ret_style}]{res['total_return_pct']:+.1f}%[/{ret_style}]",
            "Sin incluir dividendos"
        )
        summary_table.add_row(
            "Retorno Anualizado Compuesto (CAGR)",
            f"[{ret_style}]{res['annualized_cagr_pct']:+.1f}% anual[/{ret_style}]",
            "Tasa interna de retorno anual estimada"
        )
        
        signal_style = "bold green on black" if res["signal"] == "COMPRAR" else "bold red on black"
        summary_table.add_row(
            "[bold white]SEÑAL DEL MODELO[/bold white]",
            f"[{signal_style}] {res['signal']} [/{signal_style}]",
            "COMPRAR si retorno esperado > 0"
        )

        console.print(summary_table)
