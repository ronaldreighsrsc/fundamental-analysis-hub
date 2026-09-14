import os
import json
from typing import Dict, Any, Optional, List


class MoatManager:
    """
    Gestor para la evaluacion cualitativa del Foso Economico (Moat) y Tesis del Inversor.
    Carga y persiste calificaciones, fuentes de ventaja competitiva y tesis cualitativas.
    """

    SOURCE_LABELS = {
        "switching_costs": "Costes de Cambio (Switching Costs)",
        "intangibles_regulatory": "Activos Intangibles / Regulacion (Patentes, Marcas, Licencias)",
        "network_effects": "Efectos de Red (Network Effects)",
        "cost_advantages": "Ventajas de Costes / Escala",
        "efficient_scale": "Escala Eficiente (Efficient Scale)",
    }

    RATING_BADGES = {
        "Wide": "[bold green]Wide Moat (Amplio)[/bold green]",
        "Narrow": "[bold yellow]Narrow Moat (Estrecho)[/bold yellow]",
        "None": "[bold red]Sin Moat (Vulnerable)[/bold red]",
    }

    TREND_BADGES = {
        "Increasing": "[bold green][+] En Expansion[/bold green]",
        "Stable": "[bold cyan][=] Estable[/bold cyan]",
        "Decreasing": "[bold red][-] En Erosion[/bold red]",
    }

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, "config", "moat_ratings.json")
        self.config_path = config_path
        self.ratings = self._load_ratings()

    def _load_ratings(self) -> Dict[str, Any]:
        """Carga el archivo de tesis de moat desde disco."""
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_ratings(self) -> bool:
        """Guarda las calificaciones en disco."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.ratings, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get_moat(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Retorna la informacion cualitativa de moat para un ticker dado."""
        return self.ratings.get(ticker.upper())

    def get_all_moats(self) -> Dict[str, Any]:
        """Retorna todas las evaluaciones de moat registradas."""
        return self.ratings

    def set_moat(
        self,
        ticker: str,
        name: str,
        rating: str,
        trend: str,
        sources: List[str],
        thesis: str,
        threats: str,
    ) -> bool:
        """Registra o actualiza la evaluacion cualitativa de un ticker."""
        self.ratings[ticker.upper()] = {
            "name": name,
            "rating": rating,
            "trend": trend,
            "sources": sources,
            "thesis": thesis,
            "threats": threats,
        }
        return self._save_ratings()

    @classmethod
    def get_source_label(cls, source_key: str) -> str:
        """Retorna la descripcion amigable de una fuente de foso."""
        return cls.SOURCE_LABELS.get(source_key, source_key)

    @classmethod
    def get_rating_badge(cls, rating: str) -> str:
        """Retorna el badge con icono para la clasificacion del foso."""
        return cls.RATING_BADGES.get(rating, rating or "N/A")

    @classmethod
    def get_trend_badge(cls, trend: str) -> str:
        """Retorna el badge con icono para la tendencia del foso."""
        return cls.TREND_BADGES.get(trend, trend or "N/A")
