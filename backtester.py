import numpy as np
import pandas as pd
import pandas_ta as ta

class Backtester:
    #Create initial capital of 100000, fee rate of 0.01% and max weight per trade as 5% of equity
    def __init__(self,price_df,signal_df,initial_capital=100000,fee_rate=0.0001,max_weight=0.05,stop_loss_pct=0.05):
        #initialise dataframe and signals from volume-bollinger signal dataframe
        self.price_df = price_df.copy()
        self.price_df["date"] = pd.to_datetime(self.price_df["date"])
        self.price_df = self.price_df.sort_values("date")

        self.signal_df = signal_df.copy()
        self.signal_df["date"] = pd.to_datetime(self.signal_df["date"])
        self.signal_df = self.signal_df.sort_values("date")

        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.max_weight = max_weight
        self.stop_loss_pct = stop_loss_pct

        
        self.positions = {}
        self.entry_price = {}
        #history to visualise equity change
        #trade log to calculate performance ratios
        self.history = []
        self.trade_log = []
        return

    #function to determine current price at specific date and symbol
    def current_price(self,ticker,date):
        row = self.price_df[
            (self.price_df["stock_symbol"] == ticker) &
            (self.price_df["date"] == date)
            ]

        return float(row["close_price"].iloc[0])

    #calculates existing cash position and equity to determine total equity at specific date
    def mark_to_market(self,date):
        equity = self.cash
        for t, quantity in self.positions.items():
            px = self.current_price(t, date)
            if px is not None:
                equity += quantity*px
        return equity

    #For opening new position
    def open_position(self,ticker,side,price,equity_now):
        #side represents long or short
        target_value = equity_now *self.max_weight
        quantity = target_value/price
        fee = target_value* self.fee_rate

        if side == "long":
            cost = target_value + fee
            if self.cash >= cost:
                self.cash -= cost
                #Establishes new total position on a ticker by adding new quantity
                self.positions[ticker] = self.positions.get(ticker,0) + quantity
                self.entry_price[ticker] = price
        #Treats opening short position as returns with costs counted when position bought back
        elif side == "short":
            returns = target_value - fee
            self.cash += returns
            self.positions[ticker] = self.positions.get(ticker,0) - quantity
            self.entry_price[ticker] = price

        return

    def close_position(self, ticker, price, date):

        quantity = self.positions.get(ticker, 0)
        if quantity == 0:
            return
        #initialises pnl for the trade and records entry price
        entry = self.entry_price.get(ticker)
        pnl = 0

        #close position (long and short) and takes absolute quantity for short positions
        #exiting a long position counts as returns so added to cash position and exiting a short positions counts as costs and taken away from cash position
        if quantity > 0:
            returns = quantity*price - quantity*price*self.fee_rate
            pnl = (price - entry) *quantity
            self.cash += returns
        #needs to be absolute quantity since share quantity can't be below 0
        elif quantity < 0:
            absolute_qty = abs(quantity)
            cost = absolute_qty*price + absolute_qty*price*self.fee_rate
            pnl = (entry - price)*absolute_qty
            self.cash -= cost

        #Record trade with all details
        self.trade_log.append({
            "ticker": ticker,
            "entry_price": entry,
            "exit_price": price,
            "qty": quantity,
            "pnl": pnl,
            "date_exit": date
        })

        #reset position following exit
        self.positions[ticker] = 0
        self.entry_price[ticker] = None
        return

    def apply_stop_loss(self,date):
        #stop loss set at 5% range of initial entry
        close_list = []
        #ensures position exists and skips if position or entry price is non-existent
        for t, quantity in self.positions.items():
            if quantity == 0:
                continue

            px = self.current_price(t,date)
            entry = self.entry_price.get(t)
            if px is None or entry is None:
                continue

            #stop-loss for a long position
            if quantity > 0 and px <= entry*(1 -self.stop_loss_pct):
                close_list.append(t)

            #stop-loss for a short position
            if quantity < 0 and px >= entry*(1 +self.stop_loss_pct):
                close_list.append(t)

        for t in close_list:
            px = self.current_price(t,date)
            self.close_position(t,px,date)

        return

    def execute_signal(self,ticker,signal,price,date):
        quantity = self.positions.get(ticker,0)

        #buy signal
        if signal == "buy":
            
            if quantity < 0:  
                #closes short if short exists
                self.close_position(ticker,price,date)

            if quantity == 0:
                #opens long position only if current position quantity is 0
                equity_now = self.mark_to_market(date)
                self.open_position(ticker,"long",price,equity_now)

        #sell signal
        elif signal == "sell":

            if quantity > 0:
                # closes long if long position exists
                self.close_position(ticker,price,date)

            if quantity == 0:
                #opens new short position
                equity_now = self.mark_to_market(date)
                self.open_position(ticker,"short",price,equity_now)

        return

    def run(self):
        #initialises signal index to start at row 0
        all_dates = sorted(self.price_df["date"].unique())
        signal_index = 0
        total_signals = len(self.signal_df)
        #checks for stop loss signals first
        #followed by rest of buy or sell signals for each date
        for d in all_dates:

            self.apply_stop_loss(d)
            while signal_index < total_signals and self.signal_df.iloc[signal_index]["date"] == d:
                row = self.signal_df.iloc[signal_index]
                px = self.current_price(row["ticker"], d)
                #executes trade at price, date and ticker based on signal
                if px is not None:
                    self.execute_signal(row["ticker"], row["signal"], px, d)
                #signal index moves to next date after each day
                signal_index += 1

            #record equity changes
            self.history.append({
                "date": d,
                "equity": self.mark_to_market(d)
            })

        return pd.DataFrame(self.history)