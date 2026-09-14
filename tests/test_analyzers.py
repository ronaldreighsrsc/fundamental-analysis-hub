import pytest
from src.analysis.analyzer_factory import AnalyzerFactory
from src.analysis.equity_analyzer import EquityAnalyzer
from src.analysis.reit_analyzer import ReitAnalyzer
from src.analysis.etf_analyzer import EquityEtfAnalyzer, BondEtfAnalyzer


@pytest.fixture
def sample_equity_data():
    """Datos simulados de una accion con estados financieros anuales."""
    return {
        "ticker": "TEST",
        "info": {
            "longName": "Test Company Inc.",
            "currentPrice": 150.0,
            "marketCap": 200_000_000_000,
            "trailingPE": 25.5,
            "forwardPE": 22.0,
            "pegRatio": 1.5,
            "dividendYield": 0.015,
            "payoutRatio": 0.35,
            "returnOnEquity": 0.28,
            "returnOnAssets": 0.14,
            "debtToEquity": 65.0,
            "currentRatio": 1.5,
            "heldPercentInsiders": 0.12,
            "heldPercentInstitutions": 0.75,
            "sector": "Technology"
        },
        "annual": {
            "income_statement": {
                "2025": {
                    "Total Revenue": 100_000_000,
                    "Gross Profit": 50_000_000,
                    "Operating Income": 25_000_000,
                    "Net Income": 20_000_000,
                    "EBIT": 25_000_000,
                    "Tax Rate For Calcs": 0.20
                },
                "2024": {
                    "Total Revenue": 90_000_000,
                    "Gross Profit": 45_000_000,
                    "Operating Income": 22_000_000,
                    "Net Income": 18_000_000,
                    "EBIT": 22_000_000,
                    "Tax Rate For Calcs": 0.20
                }
            },
            "balance_sheet": {
                "2025": {
                    "Total Debt": 30_000_000,
                    "Stockholders Equity": 70_000_000,
                    "Cash And Cash Equivalents": 10_000_000
                }
            },
            "cash_flow": {
                "2025": {
                    "Free Cash Flow": 18_000_000
                }
            }
        }
    }


@pytest.fixture
def sample_reit_data():
    """Datos simulados de un REIT."""
    return {
        "ticker": "OREIT",
        "info": {
            "longName": "Realty Test Corp",
            "currentPrice": 60.0,
            "priceToBook": 1.4,
            "dividendYield": 0.055,
            "debtToEquity": 80.0,
            "sector": "Real Estate"
        },
        "annual": {
            "income_statement": {
                "2025": {
                    "Net Income": 1_000_000_000,
                    "Total Revenue": 4_000_000_000
                }
            },
            "cash_flow": {
                "2025": {
                    "Depreciation And Amortization": 1_500_000_000,
                    "Cash Dividends Paid": -1_800_000_000
                }
            }
        }
    }


def test_analyzer_factory(sample_equity_data, sample_reit_data):
    eq = AnalyzerFactory.create("TEST", sample_equity_data, "equity")
    assert isinstance(eq, EquityAnalyzer)
    assert eq.get_asset_type() == "equity"

    reit = AnalyzerFactory.create("OREIT", sample_reit_data, "reit")
    assert isinstance(reit, ReitAnalyzer)
    assert reit.get_asset_type() == "reit"

    with pytest.raises(ValueError):
        AnalyzerFactory.create("UNKNOWN", sample_equity_data, "cryptocurrency")


def test_equity_analyzer_margins_and_roic(sample_equity_data):
    analyzer = EquityAnalyzer("TEST", sample_equity_data)
    
    # Gross Margin: 50M / 100M = 50%
    assert analyzer._calc_gross_margin("2025") == 0.50
    # Operating Margin: 25M / 100M = 25%
    assert analyzer._calc_operating_margin("2025") == 0.25
    # Net Margin: 20M / 100M = 20%
    assert analyzer._calc_net_margin("2025") == 0.20
    # FCF Margin: 18M / 100M = 18%
    assert analyzer._calc_fcf_margin("2025") == 0.18

    # ROIC = NOPAT / (Debt + Equity - Cash)
    # NOPAT = 25M * (1 - 0.20) = 20M
    # Invested Capital = 30M + 70M - 10M = 90M
    # ROIC = 20M / 90M ≈ 0.2222
    roic = analyzer._calc_roic("2025")
    assert round(roic, 4) == round(20_000_000 / 90_000_000, 4)


def test_equity_analyzer_ownership_metrics(sample_equity_data):
    analyzer = EquityAnalyzer("TEST", sample_equity_data)
    metrics = analyzer.get_key_metrics()
    
    assert "ownership" in metrics
    assert metrics["ownership"]["held_percent_insiders"] == 0.12
    assert metrics["ownership"]["held_percent_institutions"] == 0.75

    summary = analyzer.get_summary()
    assert summary["held_percent_insiders"] == 0.12
    assert summary["held_percent_institutions"] == 0.75


def test_reit_analyzer_ffo_calculation(sample_reit_data):
    analyzer = ReitAnalyzer("OREIT", sample_reit_data)
    
    # FFO = Net Income (1000M) + Depr (1500M) = 2500M
    ffo_2025 = analyzer._calc_ffo("2025")
    assert ffo_2025 == 2_500_000_000

    metrics = analyzer.get_key_metrics()
    ffo_analysis = metrics.get("ffo_analysis", {}).get("2025", {})
    assert ffo_analysis.get("ffo") == 2_500_000_000
    
    # FFO Payout Ratio = 1800M / 2500M = 72%
    assert round(ffo_analysis.get("ffo_payout_ratio"), 2) == 0.72
