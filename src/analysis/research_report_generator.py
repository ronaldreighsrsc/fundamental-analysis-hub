import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.data.sec_financial_extractor import SecFinancialExtractor
from src.analysis.moat_manager import MoatManager
from src.valuation.graham_valuation import GrahamValuation
from src.valuation.wacc_calculator import WaccCalculator
from src.valuation.dcf_valuation import DcfValuation
from src.valuation.pe_forward_valuation import PeForwardValuation
from src.valuation.dividend_discount_model import DividendDiscountModel
from src.valuation.reverse_dcf import ReverseDcfValuation
from src.valuation.relative_multiples import RelativeMultiplesValuation
from src.portfolio.portfolio_manager import PortfolioManager


class ResearchReportGenerator:
    """
    Generador institucional de Reportes de Cobertura y Tesis de Inversión (Equity Research One-Pager).
    Integra los 3 Pilares del Análisis Fundamental:
    1. Análisis de Negocio y Foso Económico (Moat & Insider Ownership).
    2. Estados Financieros Oficiales SEC 10-K, Escudo de Solvencia y Dilución (SBC).
    3. Suite Multi-Modelo de Valuación Intrínseca y Relativa (Consenso de Fair Value).
    """

    def __init__(
        self,
        extractor: Optional[SecFinancialExtractor] = None,
        moat_mgr: Optional[MoatManager] = None,
        portfolio_mgr: Optional[PortfolioManager] = None,
        reports_dir: Optional[str] = None,
    ):
        self.extractor = extractor or SecFinancialExtractor()
        self.moat_mgr = moat_mgr or MoatManager()
        self.portfolio_mgr = portfolio_mgr or PortfolioManager()

        if reports_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            reports_dir = os.path.join(base_dir, "reports")
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_report_data(self, ticker: str) -> Dict[str, Any]:
        """
        Compila todos los datos cuantitativos y cualitativos necesarios para el reporte.
        """
        ticker = ticker.strip().upper()
        current_price = self.portfolio_mgr.get_current_market_price(ticker)
        company_name = self.extractor.get_company_name(ticker)

        # 1. Estados Financieros SEC 10-K
        df_sec = self.extractor.get_financial_history(ticker, period_type="annual")

        # Metricas recientes de balance y solvencia
        solvency = {}
        dilution = {}
        margins = {}
        historical_summary = []

        if not df_sec.empty:
            latest = df_sec.iloc[-1]
            solvency = {
                "current_ratio": float(latest.get("current_ratio")) if pd.notna(latest.get("current_ratio")) else None,
                "net_cash": float(latest.get("net_cash")) if pd.notna(latest.get("net_cash")) else None,
                "interest_coverage": float(latest.get("interest_coverage")) if pd.notna(latest.get("interest_coverage")) else None,
                "cash": float(latest.get("cash")) if pd.notna(latest.get("cash")) else None,
                "total_debt": float(latest.get("total_debt")) if pd.notna(latest.get("total_debt")) else None,
            }
            dilution = {
                "shares_diluted": float(latest.get("shares_diluted")) if pd.notna(latest.get("shares_diluted")) else None,
                "shares_change_yoy": float(latest.get("shares_change_yoy")) if pd.notna(latest.get("shares_change_yoy")) else None,
                "dilution_spread_pct": float(latest.get("dilution_spread_pct")) if pd.notna(latest.get("dilution_spread_pct")) else None,
            }
            margins = {
                "gross_margin_pct": float(latest.get("gross_margin_pct")) if pd.notna(latest.get("gross_margin_pct")) else None,
                "operating_margin_pct": float(latest.get("operating_margin_pct")) if pd.notna(latest.get("operating_margin_pct")) else None,
                "net_margin_pct": float(latest.get("net_margin_pct")) if pd.notna(latest.get("net_margin_pct")) else None,
                "fcf_margin_pct": float(latest.get("fcf_margin_pct")) if pd.notna(latest.get("fcf_margin_pct")) else None,
            }

            # Resumen ultimos anios
            tail_df = df_sec.tail(5)
            for period_idx, row in tail_df.iterrows():
                historical_summary.append({
                    "period": str(period_idx),
                    "revenue": float(row.get("revenue")) if pd.notna(row.get("revenue")) else None,
                    "operating_income": float(row.get("operating_income")) if pd.notna(row.get("operating_income")) else None,
                    "net_income": float(row.get("net_income")) if pd.notna(row.get("net_income")) else None,
                    "free_cash_flow": float(row.get("free_cash_flow")) if pd.notna(row.get("free_cash_flow")) else None,
                    "eps_diluted": float(row.get("eps_diluted")) if pd.notna(row.get("eps_diluted")) else None,
                    "shares_diluted": float(row.get("shares_diluted")) if pd.notna(row.get("shares_diluted")) else None,
                })

        # 2. Moat y Calidad del Negocio
        moat_info = self.moat_mgr.get_moat(ticker)
        if not moat_info:
            moat_info = {
                "name": company_name,
                "rating": "Narrow",
                "trend": "Stable",
                "sources": ["intangibles_regulatory", "cost_advantages"],
                "thesis": f"Tesis cualitativa en evaluacion para {company_name}.",
                "threats": "Presiones competitivas y dinamica macroeconomica.",
            }

        # 3. Modelos de Valuacion
        valuations = {}
        fair_values = []

        # Graham
        try:
            res_g = GrahamValuation().evaluate_ticker(ticker)
            valuations["graham"] = res_g
            if res_g.get("revised_value"):
                fair_values.append(("Graham 1974 (Yield AAA)", float(res_g["revised_value"]), 1.0))
            elif res_g.get("classic_value"):
                fair_values.append(("Graham 1962", float(res_g["classic_value"]), 1.0))
        except Exception as e:
            valuations["graham"] = {"error": str(e)}

        # WACC
        try:
            res_w = WaccCalculator().calculate_for_ticker(ticker)
            valuations["wacc"] = res_w
        except Exception as e:
            valuations["wacc"] = {"error": str(e)}

        # DCF
        try:
            res_dcf = DcfValuation().evaluate_ticker(ticker)
            valuations["dcf"] = res_dcf
            if res_dcf.get("intrinsic_value"):
                fair_values.append(("DCF Multi-Etapa (5Y)", float(res_dcf["intrinsic_value"]), 1.5))
        except Exception as e:
            valuations["dcf"] = {"error": str(e)}

        # Forward P/E
        try:
            res_pe = PeForwardValuation().evaluate_ticker(ticker)
            valuations["pe_forward"] = res_pe
            if res_pe.get("expected_price_5yr"):
                fair_values.append(("Forward P/E (Recompras/Dilución)", float(res_pe["expected_price_5yr"]), 1.2))
        except Exception as e:
            valuations["pe_forward"] = {"error": str(e)}

        # DDM (solo para dividend yield relevante > 1.5%)
        try:
            res_ddm = DividendDiscountModel().evaluate_ticker(ticker)
            valuations["ddm"] = res_ddm
            if res_ddm.get("intrinsic_value") and res_ddm.get("dividend_yield_pct", 0) >= 1.5:
                fair_values.append(("Dividend Discount (Gordon)", float(res_ddm["intrinsic_value"]), 0.8))
        except Exception as e:
            valuations["ddm"] = {"error": str(e)}

        # Reverse DCF
        try:
            res_rdcf = ReverseDcfValuation().evaluate_ticker(ticker)
            valuations["reverse_dcf"] = res_rdcf
        except Exception as e:
            valuations["reverse_dcf"] = {"error": str(e)}

        # Relative Multiples
        try:
            res_rel = RelativeMultiplesValuation().evaluate_ticker(ticker)
            valuations["relative_multiples"] = res_rel
            pe_hist = res_rel.get("pe_reversion", {})
            if pe_hist.get("fair_value_median_pe"):
                fair_values.append(("Reversión P/E Mediana (5Y)", float(pe_hist["fair_value_median_pe"]), 1.0))
        except Exception as e:
            valuations["relative_multiples"] = {"error": str(e)}

        # Consenso de Fair Value Ponderado
        consensus_fair_value = None
        margin_of_safety_pct = None
        recommendation = "HOLD"

        if fair_values and current_price and current_price > 0:
            total_weight = sum(w for _, _, w in fair_values)
            consensus_fair_value = sum(val * w for _, val, w in fair_values) / total_weight
            margin_of_safety_pct = ((consensus_fair_value - current_price) / consensus_fair_value) * 100

            if margin_of_safety_pct >= 15.0:
                recommendation = "BUY"
            elif margin_of_safety_pct <= -15.0:
                recommendation = "SELL"
            else:
                recommendation = "HOLD"

        return {
            "ticker": ticker,
            "company_name": company_name,
            "current_price": current_price,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "solvency": solvency,
            "dilution": dilution,
            "margins": margins,
            "history": historical_summary,
            "moat": moat_info,
            "valuations": valuations,
            "consensus": {
                "fair_value": round(consensus_fair_value, 2) if consensus_fair_value else None,
                "current_price": round(current_price, 2) if current_price else None,
                "margin_of_safety_pct": round(margin_of_safety_pct, 2) if margin_of_safety_pct is not None else None,
                "recommendation": recommendation,
                "models_used": [name for name, _, _ in fair_values],
            },
        }

    def generate_markdown_report(self, ticker: str) -> str:
        """
        Genera el documento en Markdown con formato institucional de Equity Research.
        """
        data = self.generate_report_data(ticker)
        consensus = data["consensus"]
        moat = data["moat"]
        solvency = data["solvency"]
        dilution = data["dilution"]
        margins = data["margins"]
        vals = data["valuations"]

        rec = consensus["recommendation"]
        rec_badge = "🟢 BUY (Comprar)" if rec == "BUY" else ("🟡 HOLD (Mantener)" if rec == "HOLD" else "🔴 SELL (Vender)")

        md = []
        md.append(f"# EQUITY RESEARCH INITIATING COVERAGE REPORT: {data['ticker']}")
        md.append(f"**Empresa:** {data['company_name']} | **Ticker:** `{data['ticker']}` | **Fecha:** {data['date']}")
        md.append("")
        md.append("---")
        md.append("")

        # 1. RESUMEN EJECUTIVO & RECOMENDACIÓN
        md.append("## 1. Resumen Ejecutivo & Consenso de Valuación")
        md.append("")
        md.append(f"| Métrica Clave | Valor | Descripción / Veredicto |")
        md.append(f"| :--- | :---: | :--- |")
        md.append(f"| **Recomendación Formal** | **{rec_badge}** | Tesis fundamental basada en consenso multi-modelo |")
        md.append(f"| **Precio Actual de Mercado** | `${consensus['current_price'] or 0.0:.2f}` | Último cierre registrado en mercado |")
        md.append(f"| **Valor Justo Intrínseco (Consenso)** | `${consensus['fair_value'] or 0.0:.2f}` | Promedio ponderado de modelos fundamentales |")
        mos_str = f"{consensus['margin_of_safety_pct']:+.1f}%" if consensus['margin_of_safety_pct'] is not None else "N/A"
        md.append(f"| **Margen de Seguridad** | **{mos_str}** | Descuento / Prima respecto al valor intrínseco |")
        md.append(f"| **Calificación de Foso (Moat)** | `{moat.get('rating', 'N/A')}` | Ventaja competitiva estructural sostenida |")
        md.append("")

        if consensus["margin_of_safety_pct"] and consensus["margin_of_safety_pct"] >= 15:
            md.append("> [!TIP]")
            md.append(f"> **Tesis Alcista (Bullish):** La acción cotiza con un **Margen de Seguridad atractivo de {consensus['margin_of_safety_pct']:.1f}%** frente a nuestro consenso de valor intrínseco (${consensus['fair_value']:.2f}). Se recomienda acumulación sistemática.")
        elif consensus["margin_of_safety_pct"] and consensus["margin_of_safety_pct"] <= -15:
            md.append("> [!WARNING]")
            md.append(f"> **Tesis de Cautela (Bearish):** La acción cotiza con una prima del **{abs(consensus['margin_of_safety_pct']):.1f}%** por encima de su valor intrínseco fundamental. El mercado descuenta expectativas agresivas de crecimiento.")
        else:
            md.append("> [!NOTE]")
            md.append(f"> **Tesis Neutral (Fair Value):** La cotización de mercado se encuentra alineada con el valor fundamental (${consensus['fair_value'] or 0.0:.2f}). Se recomienda mantener posiciones existentes.")

        md.append("")
        md.append("---")
        md.append("")

        # 2. PILAR #1: ANÁLISIS DE NEGOCIO Y FOSO ECONÓMICO (MOAT)
        md.append("## 2. Pilar #1: Análisis de Negocio, Foso Económico & Gobernanza")
        md.append("")
        md.append(f"- **Calificación de Moat:** `{moat.get('rating', 'None')}`")
        md.append(f"- **Tendencia del Foso:** `{moat.get('trend', 'Stable')}`")
        sources_list = [MoatManager.get_source_label(s) for s in moat.get("sources", [])]
        md.append(f"- **Fuentes de Ventaja Competitiva:** {', '.join(sources_list) if sources_list else 'En evaluación'}")
        md.append("")
        md.append("### Tesis Cualitativa del Negocio")
        md.append(f"> {moat.get('thesis', 'Tesis en proceso de documentación.')}")
        md.append("")
        md.append("### Riesgos de Disrupción y Amenazas")
        md.append(f"> {moat.get('threats', 'Monitoreo de competencia y amenazas regulatorias.')}")
        md.append("")
        md.append("---")
        md.append("")

        # 3. PILAR #2: ESTADOS FINANCIEROS Y ESCUDO DE SOLVENCIA
        md.append("## 3. Pilar #2: Estados Financieros SEC 10-K & Escudo de Solvencia")
        md.append("")
        md.append("### Métricas de Solvencia y Salud Financiera")
        cr = f"{solvency.get('current_ratio'):.2f}x" if solvency.get('current_ratio') else "N/A"
        ic = f"{solvency.get('interest_coverage'):.1f}x" if solvency.get('interest_coverage') else "N/A"
        nc = f"${solvency.get('net_cash') / 1e9:.2f}B" if solvency.get('net_cash') else "N/A"
        csh = f"${solvency.get('cash') / 1e9:.2f}B" if solvency.get('cash') else "N/A"
        dbt = f"${solvency.get('total_debt') / 1e9:.2f}B" if solvency.get('total_debt') else "N/A"

        md.append(f"| Indicador de Balance | Valor | Heurística de Seguridad Financiera |")
        md.append(f"| :--- | :---: | :--- |")
        md.append(f"| **Current Ratio (Liquidez)** | `{cr}` | > 1.2x denota cobertura holgada de pasivos corrientes |")
        md.append(f"| **Cobertura de Intereses** | `{ic}` | EBIT / Intereses. > 5.0x minimiza riesgo de impago |")
        md.append(f"| **Posición Neta de Caja** | `{nc}` | Caja (${csh}) menos Deuda Total (${dbt}) |")
        md.append("")

        md.append("### El Asesino Silencioso: Auditoría de Dilución y Stock-Based Compensation (SBC)")
        dil_chg = f"{dilution.get('shares_change_yoy'):+.2f}%" if dilution.get('shares_change_yoy') is not None else "N/A"
        dil_spr = f"{dilution.get('dilution_spread_pct'):.2f}%" if dilution.get('dilution_spread_pct') is not None else "N/A"
        sh_cnt = f"{dilution.get('shares_diluted') / 1e6:.1f}M" if dilution.get('shares_diluted') else "N/A"

        md.append(f"- **Acciones Diluidas en Circulación:** `{sh_cnt}`")
        md.append(f"- **Variación Interanual de Acciones (YoY):** `{dil_chg}` (Valores negativos indican recompra neta; positivos indican dilución)")
        md.append(f"- **Spread de Dilución por Opciones/RSUs:** `{dil_spr}` de acciones adicionales potenciales")
        md.append("")

        if data["history"]:
            md.append("### Desempeño Multianual Consolidado (SEC EDGAR 10-K)")
            md.append("")
            md.append("| Periodo | Ingresos ($) | EBIT ($) | Beneficio Neto ($) | FCF ($) | EPS Diluido | Acciones (M) |")
            md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
            for h in data["history"]:
                rev_s = f"${h['revenue']/1e9:.1f}B" if h['revenue'] else "N/A"
                ebit_s = f"${h['operating_income']/1e9:.1f}B" if h['operating_income'] else "N/A"
                ni_s = f"${h['net_income']/1e9:.1f}B" if h['net_income'] else "N/A"
                fcf_s = f"${h['free_cash_flow']/1e9:.1f}B" if h['free_cash_flow'] else "N/A"
                eps_s = f"${h['eps_diluted']:.2f}" if h['eps_diluted'] else "N/A"
                sh_s = f"{h['shares_diluted']/1e6:.1f}" if h['shares_diluted'] else "N/A"
                md.append(f"| {h['period']} | {rev_s} | {ebit_s} | {ni_s} | {fcf_s} | {eps_s} | {sh_s} |")
            md.append("")

        md.append("---")
        md.append("")

        # 4. PILAR #3: MATRIZ MULTI-MODELO DE VALUACIÓN INTRÍNSECA
        md.append("## 4. Pilar #3: Matriz Multi-Modelo de Valuación Intrínseca")
        md.append("")
        md.append("| Modelo de Valuación | Fair Value ($) | Margen vs Mercado | Notas Metodológicas |")
        md.append("| :--- | :---: | :---: | :--- |")

        # Graham
        g_res = vals.get("graham", {})
        if g_res.get("revised_value"):
            fv_g = float(g_res["revised_value"])
            mos_g = ((fv_g - consensus["current_price"]) / fv_g * 100) if fv_g else 0.0
            md.append(f"| **Benjamin Graham 1974** | `${fv_g:.2f}` | `{mos_g:+.1f}%` | Ajustado por yield bono corporativo AAA ({g_res.get('bond_yield_pct', 0.0):.2f}% en vivo de FRED) |")
        elif g_res.get("classic_value"):
            fv_g = float(g_res["classic_value"])
            mos_g = ((fv_g - consensus["current_price"]) / fv_g * 100) if fv_g else 0.0
            md.append(f"| **Benjamin Graham 1962** | `${fv_g:.2f}` | `{mos_g:+.1f}%` | Fórmula clásica sin ajuste de bonos |")

        # DCF
        dcf_res = vals.get("dcf", {})
        if dcf_res.get("intrinsic_value"):
            fv_dcf = float(dcf_res["intrinsic_value"])
            mos_dcf = ((fv_dcf - consensus["current_price"]) / fv_dcf * 100) if fv_dcf else 0.0
            md.append(f"| **DCF Multi-Etapa (5Y)** | `${fv_dcf:.2f}` | `{mos_dcf:+.1f}%` | Tasa WACC {dcf_res.get('discount_rate_pct', 0.0):.1f}%, Crecimiento Terminal {dcf_res.get('perpetual_growth_pct', 0.0):.1f}% |")

        # Forward PE
        pe_res = vals.get("pe_forward", {})
        if pe_res.get("expected_price_5yr"):
            fv_pe = float(pe_res["expected_price_5yr"])
            mos_pe = ((fv_pe - consensus["current_price"]) / fv_pe * 100) if fv_pe else 0.0
            md.append(f"| **Forward P/E Dilution-Aware** | `${fv_pe:.2f}` | `{mos_pe:+.1f}%` | EPS proyectado 5Y ${pe_res.get('final_forward_eps', 0.0):.2f} a {pe_res.get('target_pe_5yr', 0.0):.1f}x P/E con recompras |")

        # DDM
        ddm_res = vals.get("ddm", {})
        if ddm_res.get("intrinsic_value") and ddm_res.get("dividend_yield_pct", 0) >= 0.5:
            fv_ddm = float(ddm_res["intrinsic_value"])
            mos_ddm = ((fv_ddm - consensus["current_price"]) / fv_ddm * 100) if fv_ddm else 0.0
            md.append(f"| **Dividend Discount (Gordon)** | `${fv_ddm:.2f}` | `{mos_ddm:+.1f}%` | Retorno exigido {ddm_res.get('required_return_pct', 0.0):.1f}%, Crecimiento Divs {ddm_res.get('dividend_growth_rate_pct', 0.0):.1f}% |")

        # Reversion PE
        rel_res = vals.get("relative_multiples", {})
        pe_hist = rel_res.get("pe_reversion", {})
        if pe_hist.get("fair_value_median_pe"):
            fv_rev = float(pe_hist["fair_value_median_pe"])
            mos_rev = ((fv_rev - consensus["current_price"]) / fv_rev * 100) if fv_rev else 0.0
            md.append(f"| **Reversión a Mediana P/E (5Y)** | `${fv_rev:.2f}` | `{mos_rev:+.1f}%` | Basado en P/E mediano histórico de {pe_hist.get('median_5y_pe', 0.0):.1f}x |")

        md.append("")

        # Reverse DCF Insight
        rdcf_res = vals.get("reverse_dcf", {})
        if rdcf_res.get("status") == "OK":
            implied_g = rdcf_res.get("implied_growth_rate_pct", 0.0)
            md.append("### Análisis de Valuación Inversa (Reverse DCF)")
            md.append(f"> **Expectativa Implícita del Mercado:** Para justificar el precio actual de `${consensus['current_price'] or 0.0:.2f}`, la compañía debe crecer su Free Cash Flow a una tasa anual compuesta (**CAGR**) de **{implied_g:.2f}%** durante los próximos 5 años.")
            md.append("")

        # Relative Multiples Insight
        rel_res = vals.get("relative_multiples", {})
        if rel_res.get("status") == "OK":
            peg = rel_res.get("peg_analysis", {})
            md.append("### Múltiplos Relativos & Ratio PEG de Peter Lynch")
            peg_val = f"{peg.get('peg_ratio'):.2f}" if peg.get('peg_ratio') else "N/A"
            md.append(f"- **Ratio PEG de Peter Lynch:** `{peg_val}` — *{peg.get('status', 'N/A')}*")
            pe_hist = rel_res.get("pe_reversion", {})
            if pe_hist.get("fair_value_median_pe"):
                md.append(f"- **Fair Value por Reversión a P/E Mediana Histórico (5Y):** `${pe_hist.get('fair_value_median_pe'):.2f}` (P/E Mediano: {pe_hist.get('median_5y_pe', 0.0):.1f}x)")
            md.append("")

        md.append("---")
        md.append("")
        md.append("## 5. Conclusión y Recomendación Institucional")
        md.append(f"Tras auditar los 3 pilares fundamentales de **{data['company_name']}** (`{data['ticker']}`):")
        md.append(f"1. **Calidad de Negocio:** Presenta una ventaja competitiva evaluada como `{moat.get('rating', 'Narrow')}`.")
        md.append(f"2. **Salud Financiera:** Cuenta con un Current Ratio de `{cr}` y un perfil de solvencia robusto.")
        md.append(f"3. **Valuación Intrínseca:** El valor razonable consensuado se sitúa en **${consensus['fair_value'] or 0.0:.2f}**, concluyendo en una recomendación formal de **{rec_badge}**.")
        md.append("")
        md.append("*Reporte generado automáticamente por Fundamental Analysis Hub — Institutional Equity Research Engine.*")

        content = "\n".join(md)
        return content

    def export_report_to_file(self, ticker: str) -> str:
        """
        Genera y persiste el reporte en disco en formato Markdown.
        Retorna la ruta absoluta del archivo generado.
        """
        ticker = ticker.strip().upper()
        content = self.generate_markdown_report(ticker)
        file_path = os.path.join(self.reports_dir, f"{ticker}_Equity_Research_Report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
