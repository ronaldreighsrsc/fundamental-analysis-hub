import math
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.portfolio.portfolio_manager import PortfolioManager

console = Console()


class WaccCalculator:
    """
    Calculadora de Costo Promedio Ponderado de Capital (WACC / Weighted Average Cost of Capital).
    Basado en el modelo oficial del curso 'Análisis Fundamental - Hecho Simple' (Fern Finance).
    
    Fórmulas:
      1. Costo De La Deuda (Kd):
         - Pre-tax Kd = Interest Expense / Total Debt
         - After-tax Kd = Pre-tax Kd * (1 - Effective Tax Rate)
         
      2. Costo Del Equity (Ke) - Modelo CAPM:
         - Ke = Risk Free Rate + Beta * (Market Return - Risk Free Rate)
         - Risk Free Rate (Rf): Bono del Tesoro USA a 10 años (US10Y)
         - Market Return (Rm): Retorno esperado del mercado S&P 500 (8.5% - 10.0%)
         
      3. Estructura de Capital:
         - Total Capital = Total Debt + Market Cap
         - Wd = Total Debt / Total Capital
         - We = Market Cap / Total Capital
         
      4. WACC:
         - WACC = (Wd * After-tax Kd) + (We * Ke)
    """

    DEFAULT_RISK_FREE_RATE = 0.042   # 4.20% (US 10-Year Treasury Yield)
    DEFAULT_MARKET_RETURN = 0.095    # 9.50% (S&P 500 Historical CAGR)
    DEFAULT_EFFECTIVE_TAX_RATE = 0.21 # 21% (US Corporate Tax Rate)

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def calculate_wacc(
        self,
        total_debt: float,
        interest_expense: float,
        market_cap: float,
        beta: float,
        tax_rate: float = DEFAULT_EFFECTIVE_TAX_RATE,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        market_return: float = DEFAULT_MARKET_RETURN,
    ) -> Dict[str, Any]:
        """
        Calcula el WACC a partir de los parámetros financieros fundamentales.
        """
        # 1. Costo de la Deuda
        interest_abs = abs(interest_expense)
        if total_debt > 0 and interest_abs > 0:
            pre_tax_kd = interest_abs / total_debt
        elif total_debt > 0:
            # Fallback a tasa de bono soberano + spread grado inversion (1.5%)
            pre_tax_kd = risk_free_rate + 0.015
        else:
            pre_tax_kd = 0.0

        clamped_tax_rate = max(0.0, min(tax_rate, 0.45))
        after_tax_kd = pre_tax_kd * (1.0 - clamped_tax_rate)

        # 2. Costo del Equity (CAPM)
        effective_beta = max(0.2, beta)
        equity_risk_premium = max(0.02, market_return - risk_free_rate)
        ke = risk_free_rate + (effective_beta * equity_risk_premium)

        # 3. Ponderaciones de Capital
        total_capital = max(1.0, total_debt + market_cap)
        weight_debt = total_debt / total_capital
        weight_equity = market_cap / total_capital

        # 4. WACC
        wacc = (weight_debt * after_tax_kd) + (weight_equity * ke)

        return {
            "wacc": round(wacc, 4),
            "wacc_pct": round(wacc * 100, 2),
            "cost_of_equity": round(ke, 4),
            "cost_of_equity_pct": round(ke * 100, 2),
            "pre_tax_cost_of_debt": round(pre_tax_kd, 4),
            "after_tax_cost_of_debt": round(after_tax_kd, 4),
            "after_tax_cost_of_debt_pct": round(after_tax_kd * 100, 2),
            "weight_debt": round(weight_debt, 4),
            "weight_debt_pct": round(weight_debt * 100, 2),
            "weight_equity": round(weight_equity, 4),
            "weight_equity_pct": round(weight_equity * 100, 2),
            "total_debt": total_debt,
            "market_cap": market_cap,
            "total_capital": total_capital,
            "beta": round(effective_beta, 2),
            "risk_free_rate_pct": round(risk_free_rate * 100, 2),
            "market_return_pct": round(market_return * 100, 2),
            "tax_rate_pct": round(clamped_tax_rate * 100, 2),
        }

    def calculate_for_ticker(
        self,
        ticker: str,
        custom_risk_free_rate: Optional[float] = None,
        custom_market_return: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extrae automáticamente las métricas de balance y mercado para calcular el WACC del ticker.
        """
        rf = custom_risk_free_rate or self.DEFAULT_RISK_FREE_RATE
        rm = custom_market_return or self.DEFAULT_MARKET_RETURN

        # 1. Obtener datos de mercado (Market Cap, Beta, Price)
        info = {}
        try:
            profile = self.portfolio_mgr.get_company_profile(ticker)
            if profile and "info" in profile:
                info = profile["info"]
        except Exception:
            pass

        market_cap = float(info.get("marketCap") or 0.0)
        beta = float(info.get("beta") or 0.0)
        current_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)

        # Fallback a yfinance fast_info si no estan en profile
        if market_cap <= 0 or current_price <= 0:
            try:
                import yfinance as yf
                yt = yf.Ticker(ticker)
                fi = getattr(yt, "fast_info", None)
                if fi:
                    if market_cap <= 0:
                        market_cap = float(getattr(fi, "market_cap", 0.0) or 0.0)
                    if current_price <= 0:
                        current_price = float(getattr(fi, "last_price", 0.0) or 0.0)
                if beta <= 0:
                    yinfo = getattr(yt, "info", {})
                    beta = float(yinfo.get("beta") or 1.0)
            except Exception:
                pass

        if beta <= 0:
            beta = 1.0

        # 2. Obtener datos de estados financieros SEC
        history = self.extractor.get_financial_history(ticker, period_type="annual")
        total_debt = 0.0
        interest_expense = 0.0
        tax_rate = self.DEFAULT_EFFECTIVE_TAX_RATE

        if not history.empty:
            latest = history.iloc[-1]
            total_debt = float(latest.get("total_debt") or 0.0)
            
            # Intento de cálculo de tasa efectiva a partir de impuestos e ingreso antes de impuestos
            operating_income = float(latest.get("operating_income") or 0.0)
            net_income = float(latest.get("net_income") or 0.0)
            if operating_income > net_income > 0:
                tax_rate = (operating_income - net_income) / operating_income

            # Si market_cap no vino de info, aproximar con shares_diluted * price
            if market_cap <= 0 and current_price > 0:
                shares = float(latest.get("shares_diluted") or latest.get("shares_basic") or 0.0)
                if shares > 0:
                    market_cap = shares * current_price

        # Fallback de deuda si es 0 y hay pasivos no corrientes
        if total_debt <= 0:
            total_debt = float(info.get("totalDebt") or 0.0)

        wacc_res = self.calculate_wacc(
            total_debt=total_debt,
            interest_expense=interest_expense,
            market_cap=market_cap,
            beta=beta,
            tax_rate=tax_rate,
            risk_free_rate=rf,
            market_return=rm,
        )

        wacc_res["ticker"] = ticker.upper()
        wacc_res["company_name"] = info.get("longName") or ticker.upper()
        wacc_res["current_price"] = current_price
        return wacc_res

    def render_terminal_table(self, res: Dict[str, Any]):
        """Renderiza una tabla visual en consola con el desglose del WACC."""
        ticker = res.get("ticker", "TICKER")
        comp = res.get("company_name", ticker)
        
        table = Table(
            title=f"[bold cyan]Modelo WACC / Costo de Capital - {ticker}[/bold cyan] ({comp})",
            header_style="bold magenta",
            border_style="cyan",
            expand=True
        )

        table.add_column("Componente", style="bold white", width=30)
        table.add_column("Métrica / Input", justify="right", style="yellow", width=18)
        table.add_column("Ponderación / Tasa", justify="right", style="green", width=18)
        table.add_column("Detalle / Fórmula", style="dim white")

        # Equity
        table.add_row(
            "Costo del Equity (Ke)",
            f"{res['cost_of_equity_pct']}%",
            f"Peso We: {res['weight_equity_pct']}%",
            f"CAPM: Rf={res['risk_free_rate_pct']}% + Beta({res['beta']}) * ERP"
        )
        
        # Debt
        table.add_row(
            "Costo de Deuda After-Tax (Kd)",
            f"{res['after_tax_cost_of_debt_pct']}%",
            f"Peso Wd: {res['weight_debt_pct']}%",
            f"Pre-tax Kd * (1 - TaxRate {res['tax_rate_pct']}%)"
        )

        # Capital totals
        table.add_row(
            "Market Cap vs Deuda Total",
            f"${res['market_cap']/1e9:.2f}B (Equity)",
            f"${res['total_debt']/1e9:.2f}B (Debt)",
            f"Capital Total: ${res['total_capital']/1e9:.2f}B"
        )

        # Final WACC
        table.add_row(
            "[bold white]WACC FINAL (Tasa de Descuento)[/bold white]",
            f"[bold green]{res['wacc_pct']}%[/bold green]",
            "[bold cyan]100.0%[/bold cyan]",
            "[bold yellow](Wd * Kd) + (We * Ke)[/bold yellow]"
        )

        console.print(table)

    evaluate_ticker = calculate_for_ticker
