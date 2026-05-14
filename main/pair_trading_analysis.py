import pandas as pd
import numpy as np
from itertools import combinations
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint, adfuller

class PairTradingAnalysis:

    def __init__(self, df):
        self.log_df = df
        return

    #Utilise rolling cointegration with Engle-Granger test between pairs of stocks
    def rolling_coint_test(self):
        print("Generating Cointegration Test")
        
        tickers = ["AAPL","AMZN","BAC","GOOGL","JNJ","JPM","LLY","MSFT","ORCL","QQQ","SPY","WMT"]
        pairs = list(combinations(tickers,2))

        results = {}
        #Creates a combination of all possible pairs within tickers list
        for t1, t2 in pairs:
            out = []
            s1 = self.log_df[t1]
            s2 = self.log_df[t2]
            #Compares the two log series with a rolling window length of 252 days (1 trading year) and trained over 504 days (2 trading years)
            for end in range(252,504):
                start = end - 252

                y = s1.iloc[start:end]
                x = s2.iloc[start:end]
                #t_stat represents test statistic from Engle-Granger
                #p_value is probability series aren't co-integrated
                
                t_stat, p_val, crit = coint(y,x)
                #beta is the hedge ratio and requires a constant to ensure intercept not 0
                x_const = sm.add_constant(x)
                beta = sm.OLS(y,x_const).fit().params[x.name]

                #spread_now represents spread at end of each rolling window
                spread_now = s1.iloc[end]-beta*s2.iloc[end]

                out.append({
                    "date": self.log_df.index[end],
                    "p_value": p_val,
                    "t_stat": t_stat,
                    "beta": beta,
                    "spread": spread_now
                })

            pair_label = f"{t1}-{t2}"
            results[pair_label] = pd.DataFrame(out).set_index("date")
        #stable pairs represent when p_value is at 5% stat significant and equivalent t-stat
        #beta_std is to ensure beta isn't excessively volatile and sign of relationship stability
        stable_pairs = []
        #Takes the percentage for which p_value & t_stat is at the right range for cointegration out of total number of rolling windows
        try:        
            for pair, df in results.items():
                p_good = (df['p_value'] < 0.05).mean()
                t_good = (df['t_stat'] < -3.8).mean() 
                beta_std = df['beta'].std()

                if p_good > 0.7 and t_good > 0.7 and beta_std < 0.5:
                    stable_pairs.append(pair)

            if len(stable_pairs) == 0:
                raise ValueError("No stable co-integration relationships found")
        
        except ValueError as e:
            print(e)

        return
