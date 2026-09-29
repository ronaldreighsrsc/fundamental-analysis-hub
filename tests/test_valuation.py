import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from src.valuation.wacc_calculator import WaccCalculator
from src.valuation.dcf_valuation import DcfValuation
from src.valuation.pe_forward_valuation import PeForwardValuation
from src.valuation.dividend_discount_model import DividendDiscountModel
from src.valuation.reverse_dcf import ReverseDcfValuation


class TestValuationSuite:
    """Suite completa de pruebas unitarias para los modelos de valuación del curso."""

    def test_wacc_calculation(self):
        """Verifica la fórmula oficial de WACC, Kd after-tax, Ke (CAPM) y ponderaciones."""
        calc = WaccCalculator()
        res = calc.calculate_wacc(
            total_debt=100_000_000_000,
            interest_expense=4_000_000_000,
            market_cap=900_000_000_000,
            beta=1.2,
            tax_rate=0.21,
            risk_free_rate=0.04,
            market_return=0.10,
        )

        # Pre-tax Kd = 4B / 100B = 4.0%
        # After-tax Kd = 4.0% * (1 - 0.21) = 3.16%
        assert res["pre_tax_cost_of_debt"] == 0.04
        assert res["after_tax_cost_of_debt_pct"] == 3.16

        # Ke = 4.0% + 1.2 * (10.0% - 4.0%) = 11.2%
        assert res["cost_of_equity_pct"] == 11.2

        # Capital Total = 1,000B -> Wd = 10%, We = 90%
        assert res["weight_debt_pct"] == 10.0
        assert res["weight_equity_pct"] == 90.0

        # WACC = (0.10 * 0.0316) + (0.90 * 0.112) = 0.00316 + 0.1008 = 0.10396 -> 10.40%
        assert res["wacc_pct"] == 10.40

    def test_dcf_calculation(self):
        """Verifica las proyecciones a 5 años, Valor Terminal (Gordon) y Margen de Seguridad."""
        dcf = DcfValuation()
        res = dcf.calculate_dcf(
            base_revenue=100_000_000,
            shares_diluted=10_000_000,
            current_price=50.0,
            revenue_growth_rates=[0.10, 0.10, 0.08, 0.06, 0.05],
            ocf_margin=0.25,
            capex_margin=0.05,
            discount_rate=0.10,
            perpetual_growth=0.025,
        )

        assert len(res["projections"]) == 5
        # Año 1: Rev = 110M, FCF = 110M * (0.25 - 0.05) = 22M
        p1 = res["projections"][0]
        assert p1["revenue"] == 110_000_000.0
        assert p1["free_cash_flow"] == 22_000_000.0
        assert p1["pv_fcf"] == round(22_000_000.0 / 1.10, 2)

        # Intrinsic Value debe ser positivo y coherente
        assert res["intrinsic_value"] > 0
        assert res["enterprise_value"] > 0
        assert res["terminal_value"] > 0
        assert res["signal"] in ("BUY", "SELL")

    def test_pe_forward_dilution_and_buybacks(self):
        """Verifica el impacto de recompras netas de acciones (buybacks) vs dilución en el EPS."""
        pe_model = PeForwardValuation()
        
        # Caso 1: Buybacks agresivos (-4% anual de acciones)
        res_buyback = pe_model.calculate_model(
            base_revenue=100_000_000,
            base_shares=10_000_000,
            current_price=100.0,
            net_margin=0.20,
            revenue_growth_rates=[0.05, 0.05, 0.05, 0.05, 0.05],
            dilution_or_buyback_rate=-0.04,
            target_pe_5yr=20.0,
        )

        # Caso 2: Dilución de acciones (+4% anual por SBC / opciones)
        res_dilution = pe_model.calculate_model(
            base_revenue=100_000_000,
            base_shares=10_000_000,
            current_price=100.0,
            net_margin=0.20,
            revenue_growth_rates=[0.05, 0.05, 0.05, 0.05, 0.05],
            dilution_or_buyback_rate=+0.04,
            target_pe_5yr=20.0,
        )

        # El Forward EPS con buybacks debe ser sustancialmente mayor que con dilución
        assert res_buyback["final_forward_eps"] > res_dilution["final_forward_eps"]
        assert res_buyback["final_shares"] < 10_000_000
        assert res_dilution["final_shares"] > 10_000_000
        assert res_buyback["total_return_pct"] > res_dilution["total_return_pct"]

    def test_dividend_discount_model(self):
        """Verifica el modelo Gordon Growth de dividendos y caso sin dividendos."""
        ddm = DividendDiscountModel()
        
        # Pagador de dividendos
        res = ddm.calculate_ddm(
            annual_dividend=2.0,
            current_price=40.0,
            dividend_growth_rate=0.04,
            required_return=0.08,
        )
        # D1 = 2.0 * 1.04 = 2.08
        # IV = 2.08 / (0.08 - 0.04) = 52.0
        assert res["intrinsic_value"] == 52.0
        assert res["signal"] == "BUY"
        assert res["margin_of_safety_pct"] == 30.0

        # No pagador de dividendos
        res_zero = ddm.calculate_ddm(
            annual_dividend=0.0,
            current_price=150.0,
        )
        assert res_zero["intrinsic_value"] == 0.0
        assert res_zero["signal"] == "NO PAGA DIVIDENDOS"

    def test_reverse_dcf_implied_growth(self):
        """Verifica que la bisección de Reverse DCF resuelva con exactitud el crecimiento implícito."""
        rdcf = ReverseDcfValuation()
        dcf = DcfValuation()

        # Generar un precio teórico a partir de un crecimiento conocido del 12%
        base_fcf = 50_000_000
        shares = 10_000_000
        known_g = 0.12
        r = 0.095
        g_term = 0.025

        # Calcular precio objetivo teórico con known_g
        pv_sum = sum((base_fcf * ((1 + known_g)**y)) / ((1 + r)**y) for y in range(1, 6))
        fcf5 = base_fcf * ((1 + known_g)**5)
        tv = (fcf5 * (1 + g_term)) / (r - g_term)
        pv_tv = tv / ((1 + r)**5)
        theoretical_price = (pv_sum + pv_tv) / shares

        # Ahora correr Reverse DCF partiendo del precio para recuperar el crecimiento
        res = rdcf.find_implied_growth(
            base_fcf=base_fcf,
            shares_diluted=shares,
            current_price=theoretical_price,
            discount_rate=r,
            perpetual_growth=g_term,
        )

        # Debe converger exactamente a 12.0% (+/- 0.2%)
        assert abs(res["implied_growth"] - known_g) < 0.005

    def test_graham_valuation_classic_and_revised(self):
        """Verifica las fórmulas de Benjamin Graham (1962 Clásica y 1974 Revisada con AAA yield)."""
        from src.valuation.graham_valuation import GrahamValuation
        graham = GrahamValuation()
        calc = graham.calculate_intrinsic_value(
            eps=4.0,
            growth_rate=10.0,
            bond_yield=4.4,
        )
        # Clásica: V = 4 * (8.5 + 2 * 10) = 4 * 28.5 = 114.0
        assert calc["classic_value"] == 114.0
        # Revisada: V = (4 * 28.5 * 4.4) / 4.4 = 114.0
        assert calc["revised_value"] == 114.0
        # Conservadora: V = (4 * (7.0 + 1 * 10) * 4.4) / 4.4 = 4 * 17 = 68.0
        assert calc["conservative_value"] == 68.0
