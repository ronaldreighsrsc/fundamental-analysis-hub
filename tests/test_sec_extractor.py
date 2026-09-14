import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.data.sec_financial_extractor import SecFinancialExtractor
from src.data.sec_edgar_downloader import SecEdgarDownloader


@pytest.fixture
def sample_sec_facts():
    """Mock completo de hechos contables XBRL US-GAAP de la SEC."""
    return {
        "cik": 123456,
        "entityName": "ACME TEST CORP",
        "facts": {
            "us-gaap": {
                # Ingresos pre-2018
                "SalesRevenueNet": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "fy": 2017,
                                "val": 50_000_000,
                                "start": "2017-01-01",
                                "end": "2017-12-31",
                                "filed": "2018-02-15"
                            }
                        ]
                    }
                },
                # Ingresos post-2018 (norma ASC 606)
                "RevenueFromContractWithCustomerExcludingAssessedTax": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "fy": 2018,
                                "val": 60_000_000,
                                "start": "2018-01-01",
                                "end": "2018-12-31",
                                "filed": "2019-02-15"
                            },
                            {
                                "form": "10-K",
                                "fy": 2019,
                                "val": 70_000_000,
                                "start": "2019-01-01",
                                "end": "2019-12-31",
                                "filed": "2020-02-15"
                            }
                        ]
                    }
                },
                "GrossProfit": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fy": 2017, "val": 25_000_000, "start": "2017-01-01", "end": "2017-12-31", "filed": "2018-02-15"},
                            {"form": "10-K", "fy": 2018, "val": 30_000_000, "start": "2018-01-01", "end": "2018-12-31", "filed": "2019-02-15"},
                            {"form": "10-K", "fy": 2019, "val": 35_000_000, "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-15"}
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fy": 2017, "val": 10_000_000, "start": "2017-01-01", "end": "2017-12-31", "filed": "2018-02-15"},
                            {"form": "10-K", "fy": 2018, "val": 12_000_000, "start": "2018-01-01", "end": "2018-12-31", "filed": "2019-02-15"},
                            {"form": "10-K", "fy": 2019, "val": 15_000_000, "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-15"}
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fy": 2017, "val": 7_500_000, "start": "2017-01-01", "end": "2017-12-31", "filed": "2018-02-15"},
                            {"form": "10-K", "fy": 2018, "val": 9_000_000, "start": "2018-01-01", "end": "2018-12-31", "filed": "2019-02-15"},
                            {"form": "10-K", "fy": 2019, "val": 11_000_000, "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-15"}
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fy": 2017, "val": 12_000_000, "start": "2017-01-01", "end": "2017-12-31", "filed": "2018-02-15"},
                            {"form": "10-K", "fy": 2018, "val": 14_000_000, "start": "2018-01-01", "end": "2018-12-31", "filed": "2019-02-15"},
                            {"form": "10-K", "fy": 2019, "val": 16_000_000, "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-15"}
                        ]
                    }
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "fy": 2017, "val": 2_000_000, "start": "2017-01-01", "end": "2017-12-31", "filed": "2018-02-15"},
                            {"form": "10-K", "fy": 2018, "val": 3_000_000, "start": "2018-01-01", "end": "2018-12-31", "filed": "2019-02-15"},
                            {"form": "10-K", "fy": 2019, "val": 4_000_000, "start": "2019-01-01", "end": "2019-12-31", "filed": "2020-02-15"}
                        ]
                    }
                },
                "WeightedAverageNumberOfDilutedSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"form": "10-K", "fy": 2017, "val": 10_000_000, "end": "2017-12-31", "filed": "2018-02-15"},
                            {"form": "10-K", "fy": 2018, "val": 9_500_000, "end": "2018-12-31", "filed": "2019-02-15"},
                            {"form": "10-K", "fy": 2019, "val": 9_000_000, "end": "2019-12-31", "filed": "2020-02-15"}
                        ]
                    }
                }
            }
        }
    }


def test_sec_extractor_multi_year_merging(sample_sec_facts):
    mock_downloader = MagicMock()
    mock_downloader.fetch_company_facts.return_value = sample_sec_facts

    extractor = SecFinancialExtractor(downloader=mock_downloader)
    df = extractor.get_financial_history("ACME")

    assert not df.empty
    # Debe contener los tres anios (2017, 2018, 2019) sin importar el cambio de tag contable en 2018
    assert list(df.index) == ["2017", "2018", "2019"]
    assert df.loc["2017", "revenue"] == 50_000_000
    assert df.loc["2018", "revenue"] == 60_000_000
    assert df.loc["2019", "revenue"] == 70_000_000


def test_sec_extractor_derived_metrics(sample_sec_facts):
    mock_downloader = MagicMock()
    mock_downloader.fetch_company_facts.return_value = sample_sec_facts

    extractor = SecFinancialExtractor(downloader=mock_downloader)
    df = extractor.get_financial_history("ACME")

    # Margenes
    # 2018: Gross Margin = 30M / 60M = 50.0%
    assert df.loc["2018", "gross_margin_pct"] == 50.0
    # 2018: Net Margin = 9M / 60M = 15.0%
    assert df.loc["2018", "net_margin_pct"] == 15.0
    
    # FCF = OCF (14M) - CapEx (3M) = 11M
    assert df.loc["2018", "free_cash_flow"] == 11_000_000

    # Crecimiento YoY de Ventas: (60M - 50M) / 50M = 20%
    assert round(df.loc["2018", "revenue_growth_yoy"], 1) == 20.0

    # Reduccion de acciones (Recompras de acciones / Buybacks):
    # 2018: 9.5M vs 10M = -5.0%
    assert round(df.loc["2018", "shares_change_yoy"], 1) == -5.0


def test_sec_downloader_cik_formatting(tmp_path):
    cache_dir = tmp_path / "sec_cache"
    cache_dir.mkdir()
    tickers_file = cache_dir / "sec_tickers.json"
    import json
    tickers_file.write_text(json.dumps({"AAPL": "320193", "DVA": "927066"}), encoding="utf-8")

    downloader = SecEdgarDownloader(cache_dir=str(cache_dir))
    cik = downloader.get_cik_for_ticker("aapl")
    
    # Debe retornar 10 digitos con ceros a la izquierda
    assert cik == "0000320193"
    assert len(cik) == 10
