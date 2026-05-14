**24HR Hackathon Backtester Task**

A simple backtester built to measure a volume-divergence & bollinger-bands signal's performance, sharpe and sortino ratios over a set period. A set of randomly chosen equities along with index futures returns were provided as part of the task. An initial strategy based on pairs-trading mean reversion was attempted but a lack of cointegration between asset pairs indicated unreliable asset correlations. Therefore, a strategy involving volume-price divergence and breaches of bollinger bands was used instead as the signal model for the backtester.

Overall, performance yielded 12% over a 5 year period, below the S&P500 comparative benchmark with a sub-optimal sharpe ratio of 0.8.

<img width="2378" height="1002" alt="image" src="https://github.com/user-attachments/assets/75d4885d-27e5-4f25-9ab0-21b82ecc53b5" />
