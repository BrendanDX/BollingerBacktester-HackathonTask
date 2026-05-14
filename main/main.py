import numpy as np
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from data_cleanser import DataCleanser
from volume_bollinger_sig import VolumeSignal
from pair_trading_analysis import PairTradingAnalysis
from backtester import Backtester

def performance_report(equity_curve, trade_log, initial_capital):

    eq = equity_curve.copy().set_index("date")
    eq["returns"] = eq["equity"].pct_change().fillna(0)

    #Total p&l
    final_value = eq["equity"].iloc[-1]
    total_pnl = final_value - initial_capital

    #ROI
    roi = total_pnl/initial_capital

    #sharpe ratio
    sharpe = (eq["returns"].mean()/eq["returns"].std())*np.sqrt(252)

    #sortino ratio
    downside = eq.loc[eq["returns"] < 0, "returns"]
    sortino = (eq["returns"].mean()/downside.std())*np.sqrt(252)

    #calculates max drawdown from cumulative maximum 
    rolling_max = eq["equity"].cummax()
    drawdown = (eq["equity"]-rolling_max)/rolling_max
    max_drawdown = drawdown.min()

    #number of trades, win rate and avg profit
    trades = pd.DataFrame(trade_log)
    number_of_trades = len(trades)

    wins = trades[trades["pnl"] > 0]
    win_rate = len(wins)/number_of_trades
    avg_profit = trades["pnl"].mean()


    return {
        "Total PnL": total_pnl,
        "ROI": roi,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Max Drawdown": max_drawdown,
        "Number of Trades": number_of_trades,
        "Win Rate": win_rate,
        "Average Profit per Trade": avg_profit
    }


def plot_bollinger_price_volume(df, ticker):
    #filter for symbol and sort by date
    graph_points = df[df["stock_symbol"] == ticker].copy()
    graph_points["date"] = pd.to_datetime(graph_points["date"])
    graph_points = graph_points.sort_values("date")
    graph_points = graph_points.set_index("date")

    close = graph_points["close_price"]
    volume = graph_points["volume"]

    #bollinger band calculations (20 day rolling window and 2 std)
    ma = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper = ma + 2*std
    lower = ma - 2*std

    figure, ax_price = plt.subplots(figsize=(12, 6))
    axis_volume = ax_price.twinx()

    #plots close prices and bollinger bands
    ax_price.plot(close.index,close,label="Close")
    ax_price.plot(upper.index,upper,linestyle="--",label="Upper Band")
    ax_price.plot(lower.index,lower,linestyle="--",label="Lower Band")
    ax_price.plot(ma.index,ma,linestyle=":",label=f"20-day MA")

    #create labels
    ax_price.set_xlabel("Date")
    ax_price.set_ylabel("Price")
    ax_price.set_title(f"{ticker} - Price, Bollinger Bands, and Volume")

    ax_price.legend(loc="upper left")

    #creates volume bar chart
    axis_volume.bar(volume.index, volume, alpha=0.5)
    axis_volume.set_ylabel("Volume")

    figure.tight_layout()
    plt.show()

if __name__ == "__main__":
    dataset = DataCleanser("/Users/brendan/Downloads/Brendan_Xu_CodingTask/input_data.csv")
    dataset = dataset.cleanse()
    symbols = ["AAPL","AMZN","BAC","GOOGL","JNJ","JPM","LLY","MSFT","ORCL","QQQ","SPY","WMT"]
    
    #analyses for potential cointegration relationships
    pairs_analysis = PairTradingAnalysis(dataset.log_df)
    pair_analysis_result = pairs_analysis.rolling_coint_test()
    if pair_analysis_result:
        print(pairs_analysis.rolling_coint_test())
    
    #lack of stable cointegration relationships unfortunately for pair-trading mean reversion strategy
    #alpha generation model continues with using a combination of bollinger bands and volume indicators

    VS = VolumeSignal(df=dataset.df, symbols=symbols)

    all_signals = []
    for s in symbols:
        sigs = VS.screener(s)
        all_signals.append(sigs)
    
    signal_df = pd.concat(all_signals).sort_values("date")


    exit_rows = []

    for _, row in signal_df.iterrows():

        #exit strategy with 5 days exit after initial entry
        entry_sig = row["signal"]
        exit_sig  = "sell" if entry_sig == "buy" else "buy"

        exit_date = row["date"] + pd.Timedelta(days=5)
        #if in future 5 days is not a trading day, then utilise the earliest next trading day to exit position 
        price_row = dataset.df[
            (dataset.df["date"] >= exit_date) &
            (dataset.df["stock_symbol"] == row["ticker"])
        ].sort_values("date").head(1)

        #Assuming not end of dataset, position existed at next available close price and date
        if not price_row.empty:
            exit_close = float(price_row["close_price"].iloc[0])
            actual_exit_date = price_row["date"].iloc[0]
        #At end of dataset and no possible exit
        else:
            exit_close = None
            actual_exit_date = exit_date

        #add exit signal
        exit_rows.append({
            "date": actual_exit_date,
            "ticker": row["ticker"],
            "signal": exit_sig,
            "close": exit_close
        })
    #Combines all signals for entry and exit into a single dataframe for backtesting
    signal_df = pd.concat([signal_df, pd.DataFrame(exit_rows)])
    signal_df = signal_df.sort_values("date").reset_index(drop=True)

    print("Running Backtest")

    bt = Backtester(
        price_df=dataset.df,
        signal_df=signal_df,
        initial_capital=100000,
        fee_rate=0.0001,
        max_weight=0.05,
        stop_loss_pct=0.05  # 5% stop-loss
    )

    print("Generating Equity Curve")
    #generates equity curve for total 5 year period
    equity_curve = bt.run()
    plt.figure(figsize=(12,5))
    plt.plot(equity_curve["date"], equity_curve["equity"])
    plt.title("Portfolio Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity ($)")
    plt.grid(True)
    plt.show()

    #plots bollinger bands and volume on a sample ticker

    plot_bollinger_price_volume(dataset.df, "AAPL")

    #generates performance report
    report = performance_report(equity_curve, bt.trade_log, bt.initial_capital)
    for a, b in report.items():
        print(f"{a}: {b}")
