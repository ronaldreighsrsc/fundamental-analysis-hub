import math
from typing import Dict, Any, Optional, Union
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.portfolio.portfolio_manager import PortfolioManager

console = Console()


class GrahamValuation:
    """
    Implementación del modelo de Valor Intrínseco de Benjamin Graham
    (Padre del Value Investing, mentor de Warren Buffett).
    
    Fórmulas soportadas:
      1. Graham Clásica (1962):
         V = EPS * (8.5 + 2g)
         
      2. Graham Revisada / Moderna (1974 - The Intelligent Investor):
         Ajusta por el entorno de tasas de interés y bonos corporativos AAA:
         V = (EPS * (8.5 + 2g) * 4.4) / Y
         Donde:
           - 8.5: Múltiplo P/E base para una empresa de 0% crecimiento.
           - g: Tasa de crecimiento esperada anual (ej. 7 para 7%).
           - 4.4: Rendimiento histórico de referencia de bonos corporativos AAA (1962).
           - Y: Rendimiento actual de bonos corporativos AAA (o bono del Tesoro a 10 años).
           
      3. Graham Conservadora (Ajuste de margen de seguridad moderno):
         V = (EPS * (7.0 + 1g) * 4.4) / Y
    """

    BENCHMARK_AAA_YIELD = 4.4  # Tasa histórica de referencia de Graham (4.4%)
    DEFAULT_CURRENT_YIELD = 4.75  # Rendimiento actual promedio de bonos grado inversión / 10Y

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

    def calculate_intrinsic_value(
        self,
        eps: float,
        growth_rate: float,
        bond_yield: float = DEFAULT_CURRENT_YIELD,
        base_pe: float = 8.5,
        growth_multiplier: float = 2.0,
    ) -> Dict[str, float]:
        """
        Calcula el valor intrínseco de Graham clásico, revisado y conservador.
        """
        if eps <= 0:
            return {
                "classic_value": 0.0,
                "revised_value": 0.0,
                "conservative_value": 0.0,
                "error": "EPS negativo o nulo (no apto para fórmula directa de Graham)"
            }

        # 1. Fórmula Clásica de Graham (1962)
        classic_pe = base_pe + (growth_multiplier * growth_rate)
        classic_value = max(0.0, eps * classic_pe)

        # 2. Fórmula Revisada de Graham (1974 con rendimiento de bonos)
        effective_yield = max(0.5, bond_yield)
        revised_value = (eps * classic_pe * self.BENCHMARK_AAA_YIELD) / effective_yield

        # 3. Fórmula Conservadora (Factor de crecimiento 1.0 en lugar de 2.0 y base 7.0)
        conservative_pe = 7.0 + (1.0 * growth_rate)
        conservative_value = (eps * conservative_pe * self.BENCHMARK_AAA_YIELD) / effective_yield

        return {
            "classic_value": round(classic_value, 2),
            "revised_value": round(revised_value, 2),
            "conservative_value": round(conservative_value, 2),
            "classic_pe": round(classic_pe, 1),
            "conservative_pe": round(conservative_pe, 1),
        }

    def evaluate_ticker(
        self,
        ticker: str,
        custom_growth_rate: Optional[float] = None,
        bond_yield: float = DEFAULT_CURRENT_YIELD,
        period_type: str = "annual",
    ) -> Dict[str, Any]:
        """
        Evalúa automáticamente una acción descargando sus datos financieros oficiales
        de la SEC y comparando su valor intrínseco de Graham contra el precio actual de mercado.
        """
        ticker_clean = ticker.strip().upper()
        df_hist = self.extractor.get_financial_history(ticker_clean, period_type=period_type)
        company_name = self.extractor.get_company_name(ticker_clean)

        if df_hist.empty or ("eps_diluted" not in df_hist.columns and "eps_basic" not in df_hist.columns):
            return {
                "ticker": ticker_clean,
                "company_name": company_name,
                "error": f"No se encontraron datos de EPS archivados en la SEC para {ticker_clean}",
            }

        # Obtener EPS más reciente reportado
        recent_row = df_hist.iloc[-1]
        eps = recent_row.get("eps_diluted")
        if pd.isna(eps) or eps is None or eps <= 0:
            eps = recent_row.get("eps_basic")

        if eps is None or pd.isna(eps) or eps <= 0:
            return {
                "ticker": ticker_clean,
                "company_name": company_name,
                "error": f"El EPS más reciente reportado es negativo o no disponible (${eps})",
            }

        eps = float(eps)

        # Determinar tasa de crecimiento estimada (g)
        # Si no se especifica, calcular la CAGR histórica del EPS de los últimos 3-5 años
        growth_rate = custom_growth_rate
        growth_source = "Personalizado" if custom_growth_rate is not None else "CAGR Histórica SEC"

        if growth_rate is None:
            eps_series = df_hist["eps_diluted"].dropna() if "eps_diluted" in df_hist.columns else df_hist["eps_basic"].dropna()
            eps_positive = eps_series[eps_series > 0]
            if len(eps_positive) >= 3:
                years_back = min(5, len(eps_positive) - 1)
                start_eps = eps_positive.iloc[-(years_back + 1)]
                end_eps = eps_positive.iloc[-1]
                if start_eps > 0 and end_eps > 0:
                    cagr = ((end_eps / start_eps) ** (1 / years_back) - 1) * 100
                    # Limitar a rango razonable (entre 2% y 25% para evitar distorsiones hiperbólicas)
                    growth_rate = max(2.0, min(cagr, 25.0))
                else:
                    growth_rate = 5.0
            else:
                growth_rate = 5.0

        growth_rate = round(float(growth_rate), 1)

        # Precio actual de mercado
        current_price = self.portfolio_mgr.get_current_market_price(ticker_clean)

        # Cálculo de valores de Graham
        calc = self.calculate_intrinsic_value(
            eps=eps,
            growth_rate=growth_rate,
            bond_yield=bond_yield,
        )

        revised_val = calc["revised_value"]
        cons_val = calc["conservative_value"]

        # Margen de Seguridad vs Precio Actual
        mos_pct = None
        verdict = "N/A"
        if current_price and current_price > 0 and revised_val > 0:
            mos_pct = round(((revised_val - current_price) / revised_val) * 100, 1)
            if mos_pct >= 30.0:
                verdict = "INFRAVALORADA (Gran Margen de Seguridad)"
            elif mos_pct >= 10.0:
                verdict = "INFRAVALORADA (Precio Favorable)"
            elif mos_pct >= -15.0:
                verdict = "VALORACIÓN JUSTA (En Rango)"
            elif mos_pct >= -35.0:
                verdict = "SOBREVALORADA"
            else:
                verdict = "ALTAMENTE SOBREVALORADA"

        return {
            "ticker": ticker_clean,
            "company_name": company_name,
            "current_price": round(current_price, 2) if current_price > 0 else None,
            "eps": round(eps, 2),
            "estimated_growth_pct": growth_rate,
            "growth_source": growth_source,
            "bond_yield_pct": bond_yield,
            "classic_value": calc["classic_value"],
            "revised_value": revised_val,
            "conservative_value": cons_val,
            "margin_of_safety_pct": mos_pct,
            "verdict": verdict,
        }

    def render_terminal_summary(self, result: Dict[str, Any]):
        """Renderiza una tarjeta rica en terminal con la valoración de Graham."""
        if "error" in result:
            console.print(f"[bold red]Error en Valuación Graham ({result.get('ticker')}):[/bold red] {result['error']}")
            return

        ticker = result["ticker"]
        name = result.get("company_name", ticker)
        price = result.get("current_price")
        revised_v = result.get("revised_value")
        cons_v = result.get("conservative_value")
        classic_v = result.get("classic_value")
        mos = result.get("margin_of_safety_pct")
        verdict = result.get("verdict", "")

        table = Table(title=f"Valoración de Benjamin Graham: {ticker} - {name}", show_header=True, header_style="bold cyan")
        table.add_column("Métrica / Parámetro", style="white")
        table.add_column("Valor", justify="right", style="bold")
        table.add_column("Detalle Metodológico", style="dim")

        table.add_row("Precio de Mercado", f"${price:.2f}" if price else "N/A", "Cotización en tiempo real")
        table.add_row("EPS Diluido (SEC 10-K)", f"${result['eps']:.2f}", "Beneficio por acción reportado")
        table.add_row("Crecimiento Anual (g)", f"{result['estimated_growth_pct']:.1f}%", result["growth_source"])
        table.add_row("Tasa Bonos AAA (Y)", f"{result['bond_yield_pct']:.2f}%", "Rendimiento bonos de referencia")
        table.add_row("---", "---", "---")
        table.add_row("Valor Graham Clásico (1962)", f"${classic_v:.2f}", "V = EPS * (8.5 + 2g)")
        table.add_row("Valor Graham Revisado (1974)", f"[bold green]${revised_v:.2f}[/bold green]", "V = (EPS * (8.5 + 2g) * 4.4) / Y")
        table.add_row("Valor Conservador Moderno", f"[bold yellow]${cons_v:.2f}[/bold yellow]", "V = (EPS * (7.0 + 1g) * 4.4) / Y")
        table.add_row("---", "---", "---")

        mos_str = "N/A"
        if mos is not None:
            sign = "+" if mos > 0 else ""
            color = "green" if mos >= 15 else ("yellow" if mos >= -15 else "red")
            mos_str = f"[{color}]{sign}{mos:.1f}%[/{color}]"

        table.add_row("Margen de Seguridad (MoS)", mos_str, "(Valor Intrínseco - Precio) / Valor")
        
        verdict_color = "green" if "INFRAVALORADA" in verdict else ("yellow" if "JUSTA" in verdict else "red")
        table.add_row("Veredicto Graham", f"[{verdict_color}]{verdict}[/{verdict_color}]", "Criterio de margen de seguridad")

        console.print()
        console.print(table)
        console.print()

    render_terminal_table = render_terminal_summary
