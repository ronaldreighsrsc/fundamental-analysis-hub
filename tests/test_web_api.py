import threading
import socket
import json
import urllib.request
import urllib.error
import pytest
from src.portfolio.portfolio_manager import PortfolioManager
from src.web.server import create_server


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def web_server_instance(tmp_path):
    """Crea e inicia una instancia aislada del servidor HTTP para testing."""
    test_data_dir = tmp_path / "web_portfolio_data"
    manager = PortfolioManager(data_dir=str(test_data_dir))
    manager.reset_portfolio(initial_cash=50_000.0)

    port = get_free_port()
    server = create_server(host="127.0.0.1", port=port, manager=manager)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url, manager

    server.shutdown()
    server.server_close()


def test_serve_static_index(web_server_instance):
    base_url, _ = web_server_instance
    req = urllib.request.urlopen(f"{base_url}/")
    assert req.status == 200
    content = req.read().decode("utf-8")
    assert "FUNDAMENTAL ANALYSIS HUB" in content
    assert "Order Ticket" in content


def test_api_portfolio(web_server_instance):
    base_url, _ = web_server_instance
    req = urllib.request.urlopen(f"{base_url}/api/portfolio")
    assert req.status == 200
    data = json.loads(req.read().decode("utf-8"))
    assert "summary" in data
    assert "positions" in data
    assert data["summary"]["cash_balance"] == 50_000.0


def test_api_quote(web_server_instance):
    base_url, _ = web_server_instance
    req = urllib.request.urlopen(f"{base_url}/api/quote?ticker=AAPL")
    assert req.status == 200
    data = json.loads(req.read().decode("utf-8"))
    assert data["ticker"] == "AAPL"
    assert "price" in data


def test_api_buy_and_sell(web_server_instance):
    base_url, _ = web_server_instance

    # 1. Comprar acciones
    buy_payload = json.dumps({
        "ticker": "TEST_WEB",
        "shares": 10,
        "price": 100.0,
        "fee": 0.0,
        "notes": "Compra test API",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/api/buy",
        data=buy_payload,
        headers={"Content-Type": "application/json"},
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200
    res_data = json.loads(res.read().decode("utf-8"))
    assert res_data["success"] is True
    assert res_data["transaction"]["ticker"] == "TEST_WEB"

    # 2. Vender la mitad
    sell_payload = json.dumps({
        "ticker": "TEST_WEB",
        "shares": 5,
        "price": 120.0,
        "fee": 0.0,
        "notes": "Venta test API",
    }).encode("utf-8")

    req_sell = urllib.request.Request(
        f"{base_url}/api/sell",
        data=sell_payload,
        headers={"Content-Type": "application/json"},
    )
    res_sell = urllib.request.urlopen(req_sell)
    assert res_sell.status == 200
    sell_data = json.loads(res_sell.read().decode("utf-8"))
    assert sell_data["success"] is True


def test_api_deposit_and_dca(web_server_instance):
    base_url, _ = web_server_instance

    # Deposito simple
    dep_payload = json.dumps({
        "amount": 500.0,
        "notes": "Aporte mensual test",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/api/deposit",
        data=dep_payload,
        headers={"Content-Type": "application/json"},
    )
    res = urllib.request.urlopen(req)
    assert res.status == 200

    # Simulacion recurrente DCA
    dca_payload = json.dumps({
        "amount": 500.0,
        "months": 3,
        "notes": "DCA test",
    }).encode("utf-8")

    req_dca = urllib.request.Request(
        f"{base_url}/api/simulate-monthly",
        data=dca_payload,
        headers={"Content-Type": "application/json"},
    )
    res_dca = urllib.request.urlopen(req_dca)
    assert res_dca.status == 200
    dca_data = json.loads(res_dca.read().decode("utf-8"))
    assert dca_data["created_count"] == 3


def test_api_buy_insufficient_funds(web_server_instance):
    base_url, _ = web_server_instance

    buy_payload = json.dumps({
        "ticker": "EXPENSIVE",
        "shares": 1000,
        "price": 1000.0,  # $1,000,000 > $50,000
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/api/buy",
        data=buy_payload,
        headers={"Content-Type": "application/json"},
    )

    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(req)
    assert excinfo.value.code == 400
