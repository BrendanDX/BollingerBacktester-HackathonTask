import pandas as pd
import numpy as np

class DataCleanser:    
    #Initialising file path and pandas dataframe
    def __init__(self, path):
        self.path = path
        self.df = None

    #Loading data into dataframe and ensuring it's in CSV format
    def load_data(self):
        try:
            if self.path.endswith('.csv'):
                self.df = pd.read_csv(self.path)
            else:
                raise ValueError("Only CSV files accepted")
            return self
        except Exception as e:
            print(f"Error loading file: {e}")
            raise

    #Ensure column headings have standardised format by removing spaces with underscore & lower case
    def standardise_columns(self):
        self.df.columns = self.df.columns.str.strip().str.lower().str.replace(' ', '_')
        print("Column formatting standardised")
        return self
    
    #For missing values, data is filled forward by taking previous datapoint
    def fill_missing_values(self):
        non_date_columns = ['open_price','high_price','low_price','close_price','volume']
        try:
            if not self.df.isnull().values.any():
                print("No missing values found")
            else:
                for i in non_date_columns:
                    missing_rows = self.df[self.df[i].isnull()]
                    print(missing_rows)
                raise ValueError("Missing values detected in columns")
        #Includes error-handling to identify datapoints that have been forward filled
        except ValueError as e:
            print(e)
            for m in range(1, len(self.df)):
                if self.df.loc[m,non_date_columns].isnull().any():
                    self.df.loc[m,non_date_columns] = self.df.loc[m-1, non_date_columns]
            return
    
    #Format all data to the correct data type
    def _format(self):
        self.df['date'] = pd.to_datetime(self.df['date'],dayfirst=True)
        self.df['stock_symbol'] = self.df['stock_symbol'].astype(str)
        split_symbols = self.df['stock_symbol'].str.split(pat='.', n=1, expand=False)
        self.df['stock_symbol'] = split_symbols.str[0]
        self.df['volume'] = self.df['volume'].astype(int)

        price_columns = ['open_price','high_price','low_price','close_price']
        for n in price_columns:
            self.df[n] = self.df[n].astype(float)
            self.df[n] = self.df[n].round(2)

        return
    
    #Makes sure OHLC are logical
    def validate_price_columns(self):
        invalid_rows = []
        non_date_columns = ['date','open_price','high_price','low_price','close_price','volume']

        for index in range(len(self.df)):
            row = self.df.iloc[index]

            invalid_open_low   = row['open_price'] < row['low_price']
            invalid_open_high  = row['open_price']  > row['high_price']
            invalid_close_low  = row['close_price'] < row['low_price']
            invalid_close_high = row['close_price'] > row['high_price']

            if invalid_open_low or invalid_open_high or invalid_close_low or invalid_close_high:
                invalid_rows.append((index,row))

        if len(invalid_rows) == 0:
            print('All OHLC values valid')
        else:
            print('Invalid OHLC rows:')
            for index,row in invalid_rows:
                print(row)
                self.df.loc[index,non_date_columns] = self.df.loc[index-1,non_date_columns]
            
        return

    #Remove any non-positive volume
    def remove_zero_volume(self):
        for n in range(1,len(self.df)):
            if self.df.loc[n,'volume'] <= 0:
                print("Invalid Volume:")
                print(self.df.iloc[n])
                self.df.loc[n,'volume'] = self.df.loc[n-1,'volume']
        return
    
    #Sort dataset by date and resets index for ease of future handling
    def sort_by_date(self):
        self.df = self.df.sort_values('date', ascending=True).reset_index(drop=True)
        return
    
    #Creates log prices for use for cointegration and ADF spread tests for potential use as part of pair-trading mean reversion signal
    def create_log_series(self):
        tickers = ["AAPL","AMZN","BAC","GOOGL","JNJ","JPM","LLY","MSFT","ORCL","QQQ","SPY","WMT"]

        self.series = {}
        self.log_series = {}

        for t in tickers:
        
            s = self.df.loc[self.df['stock_symbol'] == t, 'close_price']
            s = s.reset_index(drop=True).astype(float)
            self.series[t] = s

            log_s = np.log(s)
            self.log_series[t] = log_s.reset_index(drop=True)

        return
    
    #Combines all separate log series into single dataframe
    def combine_log_series(self):

        self.log_df = pd.DataFrame(self.log_series)
        return self.log_df
    
    def cleanse(self):        
        self.load_data()
        self.standardise_columns()
        self.fill_missing_values()
        self._format()
        self.validate_price_columns()
        self.remove_zero_volume()
        self.sort_by_date()
        self.create_log_series()
        self.combine_log_series()
        return self











