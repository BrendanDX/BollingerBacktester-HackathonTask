import numpy as np
import pandas as pd
import pandas_ta as ta

class VolumeSignal:

    def __init__(self, df, symbols):
        self.symbols = symbols
        self.df = df.copy()
        #Re-formats database for easier handling through alpha signal indicator generator
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date')

        self.market_df = self.df.pivot(index='date', columns='stock_symbol', values='close_price')

        print("VolumeSignal initialised using DataCleanser dataframe.")
        return

    #Previously built this when used to format yfinance package data
    #Unnecessary given initial data cleanse but ensures data is of correct formatting
    def _format(self):
        
        self.df = self.df.stack(level=1).reset_index()
        self.df.columns.name = None
        self.df = self.df.rename(columns={
            "Date": "date",
            "Ticker": "ticker",
            "Close": "close",
            "High": "high",
            "Open": "open",
            "Low": "low",
            "Volume": "volume"
        })
        self.df = self.df[['date','ticker','open','close','low','high','volume']]

        return
    
    #Converts dataframe into dataframe for each symbol
    def symbol_df(self,tickerID):
        self.tickerID = self.df.loc[self.df['stock_symbol'] == tickerID, ['date','close_price','volume']]
        self.tickerID = self.tickerID.set_index('date').sort_index()
        self.tickerID.columns = ['close', 'volume']
        return self.tickerID


    #Utilises bollinger bands support/resistance strategy with consecutive declining volume as reversal indicator
    def screener(self,tickerID):
        self.symbol_df(tickerID)
        self.bollinger_series = self.tickerID.ta.bbands(close=self.tickerID["close"],length=20,std=2)
        self.confirmed_days =[]
        self.confirmed_days_price = []
        self.bollinger_signal = []
        
        #Loops through entire dataset up till 2 days before end of dataset
        for n in range(0,len(self.tickerID)-2):
            A = False
            B = False
            C = False
            #Separates bollinger bands into midpoint bullish or bearish touch, and lower bound & upper bound touch
            uppctg = (self.bollinger_series.iloc[n+2,2] - self.tickerID.iloc[n+2,0])/(self.bollinger_series.iloc[n+2,2] - self.bollinger_series.iloc[n+2,0])
            lowpctg = (self.tickerID.iloc[n+2,0] - self.bollinger_series.iloc[n+2,0])/(self.bollinger_series.iloc[n+2,2] - self.bollinger_series.iloc[n+2,0])
            midbearpctg = (self.tickerID.iloc[n+2,0] - self.bollinger_series.iloc[n+2,1])/(self.bollinger_series.iloc[n+2,2] - self.bollinger_series.iloc[n+2,0])
            midbullpctg = (self.bollinger_series.iloc[n+2,1] - self.tickerID.iloc[n+2,0])/(self.bollinger_series.iloc[n+2,2] - self.bollinger_series.iloc[n+2,0])
            #Boolean variable A represents if volume is consecutively declining over 3 days
            #Boolean variable B represents if price is steadily increasing and approaching midline bollinger band or upper bound and vice versa for boolean variable C
            
            if self.tickerID.iloc[n+2,1] < self.tickerID.iloc[n+1,1] < self.tickerID.iloc[n,1]:
                A = True
            if self.tickerID.iloc[n+2,0] > self.tickerID.iloc[n+1,0] > self.tickerID.iloc[n,0] and (uppctg < 0.1 or -0.1 <midbullpctg < 0.1):
                B = True
            if self.tickerID.iloc[n+2,0] < self.tickerID.iloc[n+1,0] < self.tickerID.iloc[n,0] and (lowpctg <0.1 or -0.1 <midbearpctg <0.1):
                C = True
            #A&B represent sell signal
            #A&C represent buy signal
            if A and B:
                self.confirmed_days.append(self.tickerID.iloc[n+2].name)
                self.confirmed_days_price.append(round(float(self.tickerID.iloc[n+2,0]),2))
                self.bollinger_signal.append("sell")

            elif A and C:
                self.confirmed_days.append(self.tickerID.iloc[n+2].name)
                self.confirmed_days_price.append(round(float(self.tickerID.iloc[n+2,0]),2))
                self.bollinger_signal.append("buy")
        #Create a dataframe of date when signal generated, ticker, price & signal (buy or sell)
        return pd.DataFrame({
            "date": self.confirmed_days,
            "ticker": tickerID,
            "close": self.confirmed_days_price,
            "signal": self.bollinger_signal
        })
