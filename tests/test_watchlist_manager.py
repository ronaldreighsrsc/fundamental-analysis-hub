import os
import json
import pytest
from src.data.watchlist_manager import WatchlistManager, VALID_ASSET_TYPES


@pytest.fixture
def temp_watchlist_file(tmp_path):
    """Crea un archivo temporal para pruebas sin alterar el config original."""
    file_path = tmp_path / "test_watchlist.json"
    initial_data = [
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "type": "equity"},
        {"ticker": "O", "name": "Realty Income Corp.", "sector": "Real Estate", "type": "reit"},
        {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "sector": "Diversified", "type": "equity_etf"},
        {"ticker": "TLT", "name": "iShares 20+ Year Treasury", "sector": "Fixed Income", "type": "bond_etf"},
    ]
    file_path.write_text(json.dumps(initial_data), encoding="utf-8")
    return str(file_path)


def test_watchlist_manager_load(temp_watchlist_file):
    mgr = WatchlistManager(filepath=temp_watchlist_file)
    assert len(mgr.get_watchlist()) == 4
    assert "AAPL" in mgr.get_tickers()
    assert "O" in mgr.get_tickers()


def test_watchlist_manager_add_ticker(temp_watchlist_file):
    mgr = WatchlistManager(filepath=temp_watchlist_file)
    added = mgr.add_ticker("DVA", name="DaVita Inc.", sector="Healthcare", asset_type="equity")
    assert added is True
    assert "DVA" in mgr.get_tickers()

    # No debe permitir duplicados
    duplicate = mgr.add_ticker("DVA", name="DaVita Inc.", sector="Healthcare", asset_type="equity")
    assert duplicate is False


def test_watchlist_manager_invalid_asset_type(temp_watchlist_file):
    mgr = WatchlistManager(filepath=temp_watchlist_file)
    with pytest.raises(ValueError) as excinfo:
        mgr.add_ticker("BTC", name="Bitcoin", asset_type="crypto")
    assert "Tipo de activo invalido" in str(excinfo.value)


def test_watchlist_manager_remove_ticker(temp_watchlist_file):
    mgr = WatchlistManager(filepath=temp_watchlist_file)
    removed = mgr.remove_ticker("AAPL")
    assert removed is True
    assert "AAPL" not in mgr.get_tickers()

    # Intentar eliminar ticker inexistente
    removed_fake = mgr.remove_ticker("NONEXISTENT")
    assert removed_fake is False


def test_watchlist_manager_filter_by_type(temp_watchlist_file):
    mgr = WatchlistManager(filepath=temp_watchlist_file)
    equities = mgr.get_tickers_by_type("equity")
    reits = mgr.get_tickers_by_type("reit")
    etfs = mgr.get_tickers_by_type("equity_etf")
    bonds = mgr.get_tickers_by_type("bond_etf")

    assert equities == ["AAPL"]
    assert reits == ["O"]
    assert etfs == ["SPY"]
    assert bonds == ["TLT"]


def test_watchlist_manager_persistence(temp_watchlist_file):
    mgr1 = WatchlistManager(filepath=temp_watchlist_file)
    mgr1.add_ticker("MSFT", name="Microsoft", sector="Technology", asset_type="equity")

    # Nueva instancia que debe leer los cambios guardados
    mgr2 = WatchlistManager(filepath=temp_watchlist_file)
    assert "MSFT" in mgr2.get_tickers()
