import json
import pytest
from src.analysis.moat_manager import MoatManager


@pytest.fixture
def temp_moat_file(tmp_path):
    """Crea un archivo temporal de calificaciones de Moat para pruebas."""
    file_path = tmp_path / "test_moat_ratings.json"
    initial_data = {
        "DVA": {
            "name": "DaVita Inc.",
            "rating": "Wide",
            "trend": "Stable",
            "sources": ["intangibles_regulatory", "switching_costs"],
            "thesis": "Duopolio de dialisis con Medicare.",
            "threats": "Farmacos GLP-1."
        },
        "XYZ": {
            "name": "Generic Co.",
            "rating": "None",
            "trend": "Decreasing",
            "sources": [],
            "thesis": "Sin ventajas.",
            "threats": "Alta competencia."
        }
    }
    file_path.write_text(json.dumps(initial_data), encoding="utf-8")
    return str(file_path)


def test_moat_manager_get_moat(temp_moat_file):
    mgr = MoatManager(config_path=temp_moat_file)
    dva = mgr.get_moat("DVA")
    assert dva is not None
    assert dva["rating"] == "Wide"
    assert "switching_costs" in dva["sources"]

    # Ticker inexistente
    fake = mgr.get_moat("NONEXISTENT")
    assert fake is None


def test_moat_manager_set_moat(temp_moat_file):
    mgr = MoatManager(config_path=temp_moat_file)
    success = mgr.set_moat(
        ticker="AAPL",
        name="Apple Inc.",
        rating="Wide",
        trend="Increasing",
        sources=["switching_costs", "network_effects"],
        thesis="Ecosistema cerrado.",
        threats="Regulacion antimonopolio."
    )
    assert success is True

    # Verificar recarga
    mgr2 = MoatManager(config_path=temp_moat_file)
    aapl = mgr2.get_moat("AAPL")
    assert aapl is not None
    assert aapl["trend"] == "Increasing"


def test_moat_manager_badges_and_labels():
    # Badges de calificacion
    assert "Wide Moat" in MoatManager.get_rating_badge("Wide")
    assert "Narrow Moat" in MoatManager.get_rating_badge("Narrow")
    assert "Sin Moat" in MoatManager.get_rating_badge("None")

    # Badges de tendencia
    assert "Expansion" in MoatManager.get_trend_badge("Increasing")
    assert "Estable" in MoatManager.get_trend_badge("Stable")
    assert "Erosion" in MoatManager.get_trend_badge("Decreasing")

    # Etiquetas de fuentes
    label = MoatManager.get_source_label("switching_costs")
    assert "Switching Costs" in label or "Costes de Cambio" in label
