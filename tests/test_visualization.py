import os
import pytest
import pandas as pd
from src.visualization.financial_charts import (
    _format_currency,
    _format_pct,
    create_financial_history_chart,
)


def test_format_currency():
    assert _format_currency(1_500_000_000) == "$1.50B"
    assert _format_currency(250_000_000) == "$250.00M"
    assert _format_currency(45.50) == "$45.50"
    assert _format_currency(None) == "N/A"
    assert _format_currency(float("nan")) == "N/A"


def test_format_pct():
    assert _format_pct(15.26, decimals=1) == "15.3%"
    assert _format_pct(-3.4, decimals=1) == "-3.4%"
    assert "[green]" in _format_pct(5.0, include_sign=True)
    assert "[red]" in _format_pct(-5.0, include_sign=True)
    assert _format_pct(None) == "N/A"


def test_create_financial_history_chart(tmp_path):
    # Crear DataFrame de prueba
    data = {
        "revenue": [10e9, 12e9, 15e9],
        "net_income": [1e9, 1.5e9, 2e9],
        "free_cash_flow": [0.8e9, 1.2e9, 1.8e9],
        "net_margin_pct": [10.0, 12.5, 13.3],
        "gross_margin_pct": [40.0, 42.0, 45.0],
        "operating_margin_pct": [15.0, 18.0, 20.0],
        "fcf_margin_pct": [8.0, 10.0, 12.0],
        "shares_diluted": [500e6, 490e6, 480e6],
    }
    df = pd.DataFrame(data, index=["2023", "2024", "2025"])

    chart_file = tmp_path / "test_chart.html"
    output_path = create_financial_history_chart(
        ticker="TEST",
        df=df,
        company_name="Test Company",
        output_path=str(chart_file),
        auto_open=False,
    )

    assert os.path.exists(output_path)
    content = chart_file.read_text(encoding="utf-8")
    # Verificar que contenga elementos de Plotly
    assert "plotly" in content.lower()
    assert "TEST" in content


def test_create_chart_empty_dataframe():
    with pytest.raises(ValueError):
        create_financial_history_chart("EMPTY", pd.DataFrame(), auto_open=False)
