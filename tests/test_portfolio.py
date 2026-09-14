import pytest
from src.portfolio.portfolio_manager import PortfolioManager
from src.portfolio.portfolio_analytics import PortfolioAnalytics


@pytest.fixture
def temp_portfolio_mgr(tmp_path):
    """Crea una instancia aislada de PortfolioManager en una carpeta temporal."""
    data_dir = tmp_path / "portfolio_test"
    mgr = PortfolioManager(data_dir=str(data_dir))
    # Reiniciar con 100.000 USD
    mgr.reset_portfolio(initial_cash=100_000.0)
    return mgr


def test_initial_portfolio_state(temp_portfolio_mgr):
    summary = temp_portfolio_mgr.get_summary()
    assert summary["portfolio_value"] == 100_000.0
    assert summary["cash_balance"] == 100_000.0
    assert summary["net_deposits"] == 100_000.0
    assert summary["realized_pnl"] == 0.0
    assert summary["unrealized_pnl"] == 0.0
    assert summary["positions_count"] == 0


def test_buy_asset(temp_portfolio_mgr):
    # Comprar 10 acciones a $150 con comision $5 -> total $1.505
    tx = temp_portfolio_mgr.buy(ticker="TEST", shares=10, price=150.0, fee=5.0, notes="Primera compra")
    assert tx["type"] == "BUY"
    assert tx["total"] == 1505.0

    positions = temp_portfolio_mgr.get_positions()
    assert "TEST" in positions
    pos = positions["TEST"]
    assert pos["shares"] == 10.0
    assert pos["avg_cost"] == 150.5
    assert pos["total_cost"] == 1505.0

    summary = temp_portfolio_mgr.get_summary()
    assert summary["cash_balance"] == 100_000.0 - 1505.0


def test_dollar_cost_averaging(temp_portfolio_mgr):
    # Tranche 1: 10 acciones a $100 ($1.000)
    temp_portfolio_mgr.buy(ticker="ABC", shares=10, price=100.0, fee=0.0)
    # Tranche 2: 10 acciones a $200 ($2.000)
    temp_portfolio_mgr.buy(ticker="ABC", shares=10, price=200.0, fee=0.0)

    positions = temp_portfolio_mgr.get_positions()
    pos = positions["ABC"]
    # Total 20 acciones, costo total $3.000 -> Costo Promedio $150
    assert pos["shares"] == 20.0
    assert pos["total_cost"] == 3000.0
    assert pos["avg_cost"] == 150.0


def test_sell_asset_with_realized_pnl(temp_portfolio_mgr):
    # Comprar 20 acciones a $150 ($3.000)
    temp_portfolio_mgr.buy(ticker="ABC", shares=20, price=150.0, fee=0.0)

    # Vender 10 acciones a $200 ($2.000 recaudados)
    # Ganancia realizada: 10 * (200 - 150) = $500
    temp_portfolio_mgr.sell(ticker="ABC", shares=10, price=200.0, fee=0.0, notes="Toma de ganancias")

    positions = temp_portfolio_mgr.get_positions()
    assert "ABC" in positions
    pos = positions["ABC"]
    assert pos["shares"] == 10.0
    assert pos["total_cost"] == 1500.0
    assert pos["avg_cost"] == 150.0

    summary = temp_portfolio_mgr.get_summary()
    assert summary["realized_pnl"] == 500.0
    # Efectivo: 100.000 - 3.000 + 2.000 = 99.000
    assert summary["cash_balance"] == 99_000.0


def test_sell_all_shares_closes_position(temp_portfolio_mgr):
    temp_portfolio_mgr.buy(ticker="XYZ", shares=5, price=50.0)
    temp_portfolio_mgr.sell(ticker="XYZ", shares=5, price=60.0)

    positions = temp_portfolio_mgr.get_positions()
    assert "XYZ" not in positions


def test_insufficient_cash_raises_error(temp_portfolio_mgr):
    # Intentar comprar por mas del efectivo disponible ($100.000)
    with pytest.raises(ValueError) as excinfo:
        temp_portfolio_mgr.buy(ticker="EXPENSIVE", shares=1000, price=150.0)
    assert "Liquidez insuficiente" in str(excinfo.value)


def test_sell_more_than_owned_raises_error(temp_portfolio_mgr):
    temp_portfolio_mgr.buy(ticker="TEST", shares=5, price=100.0)
    with pytest.raises(ValueError) as excinfo:
        temp_portfolio_mgr.sell(ticker="TEST", shares=10, price=110.0)
    assert "No posees suficientes acciones" in str(excinfo.value)


def test_portfolio_persistence_across_instances(tmp_path):
    data_dir = tmp_path / "persist_test"
    mgr1 = PortfolioManager(data_dir=str(data_dir))
    mgr1.reset_portfolio(initial_cash=50_000.0)
    mgr1.buy(ticker="PERSIST", shares=10, price=100.0)

    # Crear segunda instancia apuntando al mismo directorio
    mgr2 = PortfolioManager(data_dir=str(data_dir))
    summary = mgr2.get_summary()
    positions = mgr2.get_positions()

    assert summary["cash_balance"] == 49_000.0
    assert "PERSIST" in positions
    assert positions["PERSIST"]["shares"] == 10.0


def test_portfolio_analytics(temp_portfolio_mgr):
    # Comprar acciones simuladas y evaluar distribucion
    temp_portfolio_mgr.buy(ticker="MOCK_STOCK", shares=20, price=150.0)
    analytics = PortfolioAnalytics(temp_portfolio_mgr)

    alloc = analytics.get_asset_allocation()
    assert "cash" in alloc
    assert "equity" in alloc
    assert alloc["equity"]["market_value"] == 3000.0

    conc = analytics.get_concentration_metrics()
    assert "hhi_index" in conc
    assert "top1_position_pct" in conc


def test_export_and_import_backup(temp_portfolio_mgr, tmp_path):
    temp_portfolio_mgr.buy(ticker="BACKUP_STOCK", shares=15, price=200.0, notes="Compra para backup")
    backup_file = str(tmp_path / "backup.json")

    # Exportar
    saved_path = temp_portfolio_mgr.export_backup(filepath=backup_file)
    assert saved_path == backup_file

    # Crear nuevo manager vacio y restaurar
    new_dir = tmp_path / "restored_portfolio"
    new_mgr = PortfolioManager(data_dir=str(new_dir))
    new_mgr.reset_portfolio(initial_cash=10_000.0)

    # Importar backup
    res = new_mgr.import_backup(backup_file)
    assert res["transactions_count"] >= 2
    positions = new_mgr.get_positions()
    assert "BACKUP_STOCK" in positions
    assert positions["BACKUP_STOCK"]["shares"] == 15.0


def test_export_csv(temp_portfolio_mgr, tmp_path):
    temp_portfolio_mgr.buy(ticker="CSV_STOCK", shares=5, price=50.0)
    csv_file = str(tmp_path / "transactions.csv")

    saved_path = temp_portfolio_mgr.export_csv(filepath=csv_file)
    assert saved_path == csv_file

    with open(csv_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "CSV_STOCK" in content
    assert "BUY" in content


def test_simulate_monthly_deposits(temp_portfolio_mgr):
    # Simular 4 aportes mensuales de $500 iniciando el 1 de Octubre de 2026
    created = temp_portfolio_mgr.simulate_monthly_deposits(
        monthly_amount=500.0,
        months=4,
        start_date="2026-10-01",
        day_of_month=1,
    )
    assert len(created) == 4
    assert created[0]["timestamp"].startswith("2026-10-01")
    assert created[1]["timestamp"].startswith("2026-11-01")
    assert created[2]["timestamp"].startswith("2026-12-01")
    assert created[3]["timestamp"].startswith("2027-01-01")

    summary = temp_portfolio_mgr.get_summary()
    # Initial 100.000 + (4 * 500) = 102.000
    assert summary["cash_balance"] == 102_000.0
    assert summary["net_deposits"] == 102_000.0


def test_benchmark_comparison_and_timeline(temp_portfolio_mgr):
    temp_portfolio_mgr.simulate_monthly_deposits(monthly_amount=500.0, months=3)
    temp_portfolio_mgr.buy(ticker="MOCK_STOCK", shares=10, price=100.0)

    analytics = PortfolioAnalytics(temp_portfolio_mgr)
    bench_data = analytics.get_benchmark_comparison(benchmark_ticker="SPY")

    assert bench_data["benchmark_ticker"] == "SPY"
    metrics = bench_data["metrics"]
    assert "current_nav" in metrics
    assert "cumulative_deposits" in metrics
    assert "alpha_pct" in metrics
    assert metrics["cumulative_deposits"] == 101_500.0

    timeline = bench_data["timeline"]
    assert len(timeline["dates"]) >= 3
    assert len(timeline["portfolio_nav"]) == len(timeline["dates"])
    assert len(timeline["cumulative_deposits"]) == len(timeline["dates"])
    assert len(timeline["benchmark_nav"]) == len(timeline["dates"])


