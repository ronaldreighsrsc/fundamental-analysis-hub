from typing import Dict, Any, List
from src.portfolio.portfolio_manager import PortfolioManager


class PortfolioAnalytics:
    """
    Modulo analitico para evaluar distribucion, diversificacion, exposicion sectorial
    y flujo proyectado de dividendos del portafolio.
    """

    TYPE_LABELS = {
        "equity": "Renta Variable (Acciones)",
        "reit": "Bienes Raices (REITs)",
        "equity_etf": "ETFs de Renta Variable",
        "bond_etf": "ETFs de Renta Fija (Bonos)",
        "cash": "Efectivo / Liquidez",
    }

    def __init__(self, manager: PortfolioManager):
        self.manager = manager

    def get_asset_allocation(self) -> Dict[str, Dict[str, Any]]:
        """
        Calcula la distribucion del capital por clase de activo:
        - Acciones individuales
        - REITs
        - ETFs de Renta Variable
        - ETFs de Bonos
        - Efectivo / Liquidez
        """
        summary = self.manager.get_summary()
        positions = self.manager.get_positions()
        total_nav = summary["portfolio_value"]

        allocation: Dict[str, float] = {
            "equity": 0.0,
            "reit": 0.0,
            "equity_etf": 0.0,
            "bond_etf": 0.0,
            "cash": summary["cash_balance"],
        }

        for pos in positions.values():
            a_type = pos.get("type", "equity")
            m_val = pos.get("market_value", 0.0)
            allocation[a_type] = allocation.get(a_type, 0.0) + m_val

        result = {}
        for k, val in allocation.items():
            pct = (val / total_nav * 100) if total_nav > 0 else 0.0
            result[k] = {
                "label": self.TYPE_LABELS.get(k, k.capitalize()),
                "market_value": round(val, 2),
                "weight_pct": round(pct, 2),
            }

        return result

    def get_sector_distribution(self) -> Dict[str, Dict[str, Any]]:
        """Calcula la distribucion del capital invertido por sector economico."""
        positions = self.manager.get_positions()
        summary = self.manager.get_summary()
        invested_capital = summary["positions_market_value"]

        sectors: Dict[str, float] = {}
        for pos in positions.values():
            sec = pos.get("sector", "General") or "General"
            m_val = pos.get("market_value", 0.0)
            sectors[sec] = sectors.get(sec, 0.0) + m_val

        result = {}
        for sec, val in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
            pct = (val / invested_capital * 100) if invested_capital > 0 else 0.0
            result[sec] = {
                "market_value": round(val, 2),
                "weight_pct": round(pct, 2),
            }

        return result

    def get_concentration_metrics(self) -> Dict[str, Any]:
        """Calcula metricas de concentracion y diversificacion de la cartera."""
        positions = self.manager.get_positions()
        summary = self.manager.get_summary()
        total_nav = summary["portfolio_value"]

        weights = [
            (p["market_value"] / total_nav) for p in positions.values() if total_nav > 0
        ]
        weights.sort(reverse=True)

        top1_weight = (weights[0] * 100) if len(weights) > 0 else 0.0
        top3_weight = (sum(weights[:3]) * 100) if len(weights) >= 3 else (sum(weights) * 100)

        # Indice Herfindahl-Hirschman (HHI) escala 0 a 10.000
        # HHI < 1.500: Cartera altamente diversificada
        # 1.500 <= HHI <= 2.500: Concentracion moderada
        # HHI > 2.500: Cartera altamente concentrada
        hhi = sum((w * 100) ** 2 for w in weights)

        return {
            "top1_position_pct": round(top1_weight, 2),
            "top3_positions_pct": round(top3_weight, 2),
            "hhi_index": round(hhi, 1),
            "diversification_level": (
                "Alta diversificacion" if hhi < 1500
                else "Concentracion moderada" if hhi <= 2500
                else "Alta concentracion"
            )
        }
