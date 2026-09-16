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

    def get_benchmark_comparison(self, benchmark_ticker: str = "SPY") -> Dict[str, Any]:
        """
        Reconstruye la serie temporal de evolucion del portafolio y la compara
        contra el S&P 500 (o benchmark seleccionado) utilizando la metodologia
        institucional Public Market Equivalent (PME).

        Desacopla las aportaciones de capital (inflows) de la rentabilidad real
        generada por el mercado para evitar la sobreestimacion de retornos.
        """
        from datetime import datetime
        import pandas as pd

        txs = self.manager._load_transactions()
        if not txs:
            return {
                "benchmark_ticker": benchmark_ticker,
                "timeline": {
                    "dates": [],
                    "portfolio_nav": [],
                    "cumulative_deposits": [],
                    "benchmark_nav": [],
                    "portfolio_return_pct": [],
                    "benchmark_return_pct": [],
                    "alpha_pct": [],
                },
                "metrics": {
                    "current_nav": 0.0,
                    "cumulative_deposits": 0.0,
                    "current_benchmark_val": 0.0,
                    "portfolio_return_pct": 0.0,
                    "benchmark_return_pct": 0.0,
                    "alpha_pct": 0.0,
                },
            }

        # Asegurar orden cronologico
        sorted_txs = sorted(txs, key=lambda x: x.get("timestamp", ""))

        # Identificar tickers
        tickers = list({tx["ticker"] for tx in sorted_txs if tx.get("ticker") and tx["ticker"] != "CASH"})

        # Precios de fallback basados en transacciones
        fallback_prices = {}
        for tx in sorted_txs:
            t = tx.get("ticker")
            if t and t != "CASH" and tx.get("price", 0) > 0:
                fallback_prices[t] = float(tx["price"])

        fallback_spy_price = 500.0

        # Descargar historicos de precios
        bench_df = None
        try:
            bench_df = self.manager.downloader.fetch_price_data(benchmark_ticker, period="2y")
            if bench_df is not None and not bench_df.empty and "Close" in bench_df.columns:
                fallback_spy_price = float(bench_df["Close"].iloc[-1])
        except Exception:
            bench_df = None

        price_dfs = {}
        for t in tickers:
            try:
                df_p = self.manager.downloader.fetch_price_data(t, period="2y")
                price_dfs[t] = df_p
                if df_p is not None and not df_p.empty and "Close" in df_p.columns:
                    fallback_prices[t] = float(df_p["Close"].iloc[-1])
            except Exception:
                price_dfs[t] = None

        def _lookup_price(df, target_date_str, fallback):
            if df is not None and not df.empty and "Close" in df.columns:
                try:
                    target_dt = pd.to_datetime(target_date_str)
                    sub = df.loc[df.index <= target_dt]
                    if not sub.empty:
                        return float(sub["Close"].iloc[-1])
                except Exception:
                    pass
            return fallback

        # Determinar fechas de muestreo
        first_tx_date = sorted_txs[0]["timestamp"][:10]
        today_date = datetime.now().strftime("%Y-%m-%d")

        dates = []
        if bench_df is not None and not bench_df.empty:
            try:
                dt_range = bench_df.loc[
                    (bench_df.index >= pd.to_datetime(first_tx_date)) &
                    (bench_df.index <= pd.to_datetime(today_date))
                ]
                dates = [d.strftime("%Y-%m-%d") for d in dt_range.index]
            except Exception:
                dates = []

        # Asegurar que todas las fechas de transaccion esten incluidas
        tx_dates = {tx["timestamp"][:10] for tx in sorted_txs}
        tx_dates.add(today_date)
        all_dates_set = set(dates).union(tx_dates)
        eval_dates = sorted(list(all_dates_set))

        # Si no hay fechas intermedias, al menos evaluar puntos de transaccion
        if not eval_dates:
            eval_dates = [first_tx_date, today_date]

        timeline_dates = []
        portfolio_nav_series = []
        cum_deposits_series = []
        benchmark_nav_series = []
        port_ret_series = []
        bench_ret_series = []
        alpha_series = []

        for d_str in eval_dates:
            # Reconstruir estado en la fecha d_str
            cash = 0.0
            cum_deposits = 0.0
            spy_shares = 0.0
            shares_held = {t: 0.0 for t in tickers}

            for tx in sorted_txs:
                t_date = tx["timestamp"][:10]
                if t_date > d_str:
                    break

                t_type = tx.get("type")
                t_ticker = tx.get("ticker")
                t_total = float(tx.get("total", 0.0))
                t_shares = float(tx.get("shares", 0.0))

                if t_type == "DEPOSIT":
                    cash += t_total
                    cum_deposits += t_total
                    spy_p = _lookup_price(bench_df, t_date, fallback_spy_price)
                    if spy_p > 0:
                        spy_shares += t_total / spy_p

                elif t_type == "WITHDRAW":
                    cash -= t_total
                    cum_deposits -= t_total
                    spy_p = _lookup_price(bench_df, t_date, fallback_spy_price)
                    if spy_p > 0:
                        spy_shares -= t_total / spy_p

                elif t_type == "BUY":
                    cash -= t_total
                    shares_held[t_ticker] = shares_held.get(t_ticker, 0.0) + t_shares

                elif t_type == "SELL":
                    cash += t_total
                    shares_held[t_ticker] = max(0.0, shares_held.get(t_ticker, 0.0) - t_shares)

                elif t_type == "SPLIT":
                    ratio = float(tx.get("shares", 1.0))
                    if ratio > 0:
                        shares_held[t_ticker] = shares_held.get(t_ticker, 0.0) * ratio

                elif t_type == "DIVIDEND":
                    cash += t_total

            # Valor de mercado de las acciones en fecha d_str
            stocks_val = 0.0
            for t in tickers:
                qty = shares_held.get(t, 0.0)
                if qty > 0:
                    p = _lookup_price(price_dfs.get(t), d_str, fallback_prices.get(t, 0.0))
                    stocks_val += qty * p

            nav = cash + stocks_val
            curr_spy_price = _lookup_price(bench_df, d_str, fallback_spy_price)
            bench_val = spy_shares * curr_spy_price

            port_ret = ((nav - cum_deposits) / cum_deposits * 100) if cum_deposits > 0 else 0.0
            bench_ret = ((bench_val - cum_deposits) / cum_deposits * 100) if cum_deposits > 0 else 0.0
            alpha = port_ret - bench_ret

            timeline_dates.append(d_str)
            portfolio_nav_series.append(round(nav, 2))
            cum_deposits_series.append(round(cum_deposits, 2))
            benchmark_nav_series.append(round(bench_val, 2))
            port_ret_series.append(round(port_ret, 2))
            bench_ret_series.append(round(bench_ret, 2))
            alpha_series.append(round(alpha, 2))

        latest_idx = -1 if timeline_dates else 0
        current_nav = portfolio_nav_series[latest_idx] if portfolio_nav_series else 0.0
        current_deposits = cum_deposits_series[latest_idx] if cum_deposits_series else 0.0
        current_bench = benchmark_nav_series[latest_idx] if benchmark_nav_series else 0.0
        final_port_ret = port_ret_series[latest_idx] if port_ret_series else 0.0
        final_bench_ret = bench_ret_series[latest_idx] if bench_ret_series else 0.0
        final_alpha = alpha_series[latest_idx] if alpha_series else 0.0

        # CAGR / Retorno Compuesto Anualizado
        cagr_port = 0.0
        cagr_bench = 0.0
        cagr_alpha = 0.0

        if timeline_dates and len(timeline_dates) >= 2:
            try:
                dt_start = datetime.strptime(timeline_dates[0], "%Y-%m-%d")
                dt_end = datetime.strptime(timeline_dates[-1], "%Y-%m-%d")
                days_elapsed = max(1, (dt_end - dt_start).days)
                if days_elapsed >= 7:  # Minimo 7 dias para anualizar
                    years = days_elapsed / 365.25
                    tot_factor_port = max(0.0001, 1.0 + (final_port_ret / 100.0))
                    cagr_port = round(((tot_factor_port ** (1.0 / years)) - 1.0) * 100.0, 2)

                    tot_factor_bench = max(0.0001, 1.0 + (final_bench_ret / 100.0))
                    cagr_bench = round(((tot_factor_bench ** (1.0 / years)) - 1.0) * 100.0, 2)

                    cagr_alpha = round(cagr_port - cagr_bench, 2)
            except Exception:
                pass

        return {
            "benchmark_ticker": benchmark_ticker,
            "timeline": {
                "dates": timeline_dates,
                "portfolio_nav": portfolio_nav_series,
                "cumulative_deposits": cum_deposits_series,
                "benchmark_nav": benchmark_nav_series,
                "portfolio_return_pct": port_ret_series,
                "benchmark_return_pct": bench_ret_series,
                "alpha_pct": alpha_series,
            },
            "metrics": {
                "current_nav": current_nav,
                "cumulative_deposits": current_deposits,
                "current_benchmark_val": current_bench,
                "portfolio_return_pct": final_port_ret,
                "benchmark_return_pct": final_bench_ret,
                "alpha_pct": final_alpha,
                "cagr_portfolio_pct": cagr_port,
                "cagr_benchmark_pct": cagr_bench,
                "cagr_alpha_pct": cagr_alpha,
                "start_date": timeline_dates[0] if timeline_dates else today_date,
                "end_date": timeline_dates[-1] if timeline_dates else today_date,
            },
        }

