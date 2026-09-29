from typing import Dict, Any, Optional, List
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


from src.data.sec_financial_extractor import SecFinancialExtractor
from src.portfolio.portfolio_manager import PortfolioManager

class RelativeMultiplesValuation:
    """
    Modelo de Valuación por Múltiplos Relativos y Comparables
    (Capítulo 2 y Capítulo 3 del curso 'Análisis Fundamental - Hecho Simple').
    """

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def calculate_peg_ratio(
        self,
        current_pe: float,
        expected_growth_rate_pct: float,
    ) -> Dict[str, Any]:
        """
        Calcula el ratio PEG de Peter Lynch e interpreta la valoración relativa.
        
        Args:
            current_pe: P/E actual (TTM o Forward).
            expected_growth_rate_pct: Crecimiento esperado de EPS en porcentaje (ej: 15.0 para 15%).
        """
        if expected_growth_rate_pct <= 0 or current_pe <= 0:
            return {
                "peg_ratio": None,
                "status": "No aplicable (crecimiento o P/E <= 0)",
                "signal": "NEUTRAL",
                "score": 0.0
            }

        peg = current_pe / expected_growth_rate_pct

        if peg < 1.0:
            status = "Infravalorada (Crecimiento superior al múltiplo P/E)"
            signal = "BUY"
            score = 1.0
        elif peg <= 1.5:
            status = "Valor Justo (Fair Value acorde a crecimiento)"
            signal = "HOLD"
            score = 0.5
        elif peg <= 2.0:
            status = "Ligeramente Sobrevalorada"
            signal = "HOLD"
            score = 0.0
        else:
            status = "Sobrevalorada (Múltiplo exige crecimiento poco realista)"
            signal = "SELL"
            score = -1.0

        return {
            "current_pe": round(current_pe, 2),
            "expected_growth_rate_pct": round(expected_growth_rate_pct, 2),
            "peg_ratio": round(peg, 2),
            "status": status,
            "signal": signal,
            "score": score
        }

    def calculate_pe_historical_fair_value(
        self,
        expected_eps: float,
        historical_pe_median: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Calcula el valor objetivo según el método 'Mi Favorita' (Mediana Histórica P/E).
        """
        if expected_eps <= 0 or historical_pe_median <= 0:
            return {
                "fair_value": 0.0,
                "upside_pct": 0.0,
                "signal": "AVOID",
                "reason": "EPS o mediana P/E no válidos"
            }

        target_price = historical_pe_median * expected_eps
        upside_pct = ((target_price / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0

        signal = "BUY" if upside_pct > 15.0 else ("HOLD" if upside_pct > -10.0 else "SELL")

        return {
            "expected_eps": round(expected_eps, 2),
            "historical_pe_median": round(historical_pe_median, 2),
            "current_price": round(current_price, 2),
            "fair_value": round(target_price, 2),
            "upside_pct": round(upside_pct, 2),
            "signal": signal
        }

    def calculate_ps_fair_value(
        self,
        revenue_per_share: float,
        historical_ps_median: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Calcula el valor objetivo basado en el múltiplo Price-to-Sales (P/S).
        """
        if revenue_per_share <= 0 or historical_ps_median <= 0:
            return {"fair_value": 0.0, "upside_pct": 0.0, "signal": "AVOID"}

        target_price = historical_ps_median * revenue_per_share
        upside_pct = ((target_price / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0
        signal = "BUY" if upside_pct > 15.0 else ("HOLD" if upside_pct > -10.0 else "SELL")

        return {
            "revenue_per_share": round(revenue_per_share, 2),
            "historical_ps_median": round(historical_ps_median, 2),
            "current_price": round(current_price, 2),
            "fair_value": round(target_price, 2),
            "upside_pct": round(upside_pct, 2),
            "signal": signal
        }

    def calculate_pb_fair_value(
        self,
        book_value_per_share: float,
        historical_pb_median: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Calcula el valor objetivo basado en el múltiplo Price-to-Book (P/B).
        """
        if book_value_per_share <= 0 or historical_pb_median <= 0:
            return {"fair_value": 0.0, "upside_pct": 0.0, "signal": "AVOID"}

        target_price = historical_pb_median * book_value_per_share
        upside_pct = ((target_price / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0
        signal = "BUY" if upside_pct > 15.0 else ("HOLD" if upside_pct > -10.0 else "SELL")

        return {
            "book_value_per_share": round(book_value_per_share, 2),
            "historical_pb_median": round(historical_pb_median, 2),
            "current_price": round(current_price, 2),
            "fair_value": round(target_price, 2),
            "upside_pct": round(upside_pct, 2),
            "signal": signal
        }

    def calculate_pcf_fair_value(
        self,
        operating_cf_per_share: float,
        historical_pcf_median: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Calcula el valor objetivo basado en Price-to-Operating-Cash-Flow (P/CF).
        """
        if operating_cf_per_share <= 0 or historical_pcf_median <= 0:
            return {"fair_value": 0.0, "upside_pct": 0.0, "signal": "AVOID"}

        target_price = historical_pcf_median * operating_cf_per_share
        upside_pct = ((target_price / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0
        signal = "BUY" if upside_pct > 15.0 else ("HOLD" if upside_pct > -10.0 else "SELL")

        return {
            "operating_cf_per_share": round(operating_cf_per_share, 2),
            "historical_pcf_median": round(historical_pcf_median, 2),
            "current_price": round(current_price, 2),
            "fair_value": round(target_price, 2),
            "upside_pct": round(upside_pct, 2),
            "signal": signal
        }

    def comprehensive_relative_valuation(
        self,
        current_price: float,
        eps: float,
        revenue_per_share: float,
        book_value_per_share: float,
        ocf_per_share: float,
        expected_eps_growth_pct: float,
        historical_pe_median: float = 20.0,
        historical_ps_median: float = 3.0,
        historical_pb_median: float = 3.0,
        historical_pcf_median: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Genera una síntesis integral de todos los múltiplos relativos.
        """
        current_pe = current_price / eps if eps > 0 else 0.0
        peg_res = self.calculate_peg_ratio(current_pe, expected_eps_growth_pct)
        pe_fair = self.calculate_pe_historical_fair_value(eps, historical_pe_median, current_price)
        ps_fair = self.calculate_ps_fair_value(revenue_per_share, historical_ps_median, current_price)
        pb_fair = self.calculate_pb_fair_value(book_value_per_share, historical_pb_median, current_price)
        pcf_fair = self.calculate_pcf_fair_value(ocf_per_share, historical_pcf_median, current_price)

        valid_targets = [
            m["fair_value"]
            for m in [pe_fair, ps_fair, pb_fair, pcf_fair]
            if m.get("fair_value", 0) > 0
        ]
        composite_fair_value = float(np.mean(valid_targets)) if valid_targets else 0.0
        composite_upside = ((composite_fair_value / current_price) - 1.0) * 100.0 if current_price > 0 else 0.0

        return {
            "current_price": current_price,
            "peg_analysis": peg_res,
            "pe_method_mi_favorita": pe_fair,
            "ps_method": ps_fair,
            "pb_method": pb_fair,
            "pcf_method": pcf_fair,
            "composite_multiples_fair_value": round(composite_fair_value, 2),
            "composite_upside_pct": round(composite_upside, 2),
            "composite_signal": "BUY" if composite_upside > 15.0 else ("HOLD" if composite_upside > -10.0 else "SELL")
        }

    def print_summary_table(self, ticker: str, res: Dict[str, Any]) -> None:
        """Renderiza una tabla visual en consola usando Rich."""
        table = Table(title=f"Valuación por Múltiplos Relativos: {ticker}", show_header=True)
        table.add_column("Métrica / Modelo", style="cyan", no_wrap=True)
        table.add_column("Valor Actual", justify="right")
        table.add_column("Mediana / Ref.", justify="right")
        table.add_column("Precio Objetivo", justify="right", style="green")
        table.add_column("Diferencia %", justify="right")
        table.add_column("Señal", justify="center", style="bold")

        # PEG
        peg = res.get("peg_analysis", {})
        table.add_row(
            "PEG Ratio (Lynch)",
            f"{peg.get('current_pe', '-')}x",
            f"g={peg.get('expected_growth_rate_pct', '-')}%",
            f"PEG={peg.get('peg_ratio', '-')}",
            peg.get("status", ""),
            peg.get("signal", "N/A"),
        )

        # PE Mi Favorita
        pe = res.get("pe_method_mi_favorita", {})
        table.add_row(
            "P/E ('Mi Favorita')",
            f"${res.get('current_price', 0):.2f}",
            f"{pe.get('historical_pe_median', 0):.1f}x",
            f"${pe.get('fair_value', 0):.2f}",
            f"{pe.get('upside_pct', 0):+.1f}%",
            pe.get("signal", "N/A"),
        )

        # PS
        ps = res.get("ps_method", {})
        table.add_row(
            "P/S (Price to Sales)",
            f"${res.get('current_price', 0):.2f}",
            f"{ps.get('historical_ps_median', 0):.1f}x",
            f"${ps.get('fair_value', 0):.2f}",
            f"{ps.get('upside_pct', 0):+.1f}%",
            ps.get("signal", "N/A"),
        )

        # PB
        pb = res.get("pb_method", {})
        table.add_row(
            "P/B (Price to Book)",
            f"${res.get('current_price', 0):.2f}",
            f"{pb.get('historical_pb_median', 0):.1f}x",
            f"${pb.get('fair_value', 0):.2f}",
            f"{pb.get('upside_pct', 0):+.1f}%",
            pb.get("signal", "N/A"),
        )

        # PCF
        pcf = res.get("pcf_method", {})
        table.add_row(
            "P/CF (Operating Cash Flow)",
            f"${res.get('current_price', 0):.2f}",
            f"{pcf.get('historical_pcf_median', 0):.1f}x",
            f"${pcf.get('fair_value', 0):.2f}",
            f"{pcf.get('upside_pct', 0):+.1f}%",
            pcf.get("signal", "N/A"),
        )

        console.print(table)
        console.print(
            Panel(
                f"[bold green]Precio Compuesto por Múltiplos:[/bold green] ${res.get('composite_multiples_fair_value', 0):.2f} "
                f"({res.get('composite_upside_pct', 0):+.1f}%) | "
                f"[bold]Señal Global:[/bold] {res.get('composite_signal')}",
                border_style="cyan"
            )
        )

    def evaluate_ticker(
        self,
        ticker: str,
        custom_growth_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evalúa un ticker completo extrayendo sus fundamentales de SEC y precios de mercado.
        """
        ticker_clean = ticker.strip().upper()
        df_hist = self.extractor.get_financial_history(ticker_clean, period_type="annual")
        
        if df_hist.empty:
            raise ValueError(f"No se encontraron estados financieros anuales en SEC para {ticker_clean}")

        latest = df_hist.iloc[-1]
        shares = float(latest.get("shares_diluted", 0) or latest.get("shares_basic", 0))
        if shares <= 0:
            shares = 1.0

        eps = float(latest.get("eps_diluted", 0) or latest.get("eps_basic", 0))
        revenue = float(latest.get("total_revenue", 0))
        equity = float(latest.get("stockholders_equity", 0))
        ocf = float(latest.get("operating_cash_flow", 0))

        rev_per_share = revenue / shares if shares > 0 else 0.0
        bv_per_share = equity / shares if shares > 0 else 0.0
        ocf_per_share = ocf / shares if shares > 0 else 0.0

        # Crecimiento estimado
        growth_rate = custom_growth_rate
        if growth_rate is None:
            eps_series = df_hist["eps_diluted"].dropna() if "eps_diluted" in df_hist.columns else df_hist["eps_basic"].dropna()
            eps_pos = eps_series[eps_series > 0]
            if len(eps_pos) >= 3:
                years = min(5, len(eps_pos) - 1)
                s_eps = eps_pos.iloc[-(years + 1)]
                e_eps = eps_pos.iloc[-1]
                if s_eps > 0 and e_eps > 0:
                    cagr = ((e_eps / s_eps) ** (1 / years) - 1) * 100
                    growth_rate = max(2.0, min(cagr, 25.0))
                else:
                    growth_rate = 8.0
            else:
                growth_rate = 8.0

        current_price = self.portfolio_mgr.get_current_market_price(ticker_clean)
        if not current_price or current_price <= 0:
            current_price = eps * 15.0 if eps > 0 else 100.0

        res = self.comprehensive_relative_valuation(
            current_price=float(current_price),
            eps=eps,
            revenue_per_share=rev_per_share,
            book_value_per_share=bv_per_share,
            ocf_per_share=ocf_per_share,
            expected_eps_growth_pct=float(growth_rate),
        )
        res["ticker"] = ticker_clean
        return res

    def render_terminal_table(self, res: Dict[str, Any]) -> None:
        """Alias compatible con el estándar de suites del hub."""
        ticker = res.get("ticker", "TICKER")
        self.print_summary_table(ticker, res)

