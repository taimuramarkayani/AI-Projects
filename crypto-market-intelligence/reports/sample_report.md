# Bitcoin Market Behaviour Analyzer

**Generated:** 2026-10-27 17:16 UTC

## Research question

How do Bitcoin's daily price movements and trading volume relate to its
short-term (7-day) and longer-term (30-day) price trends over the last
30 completed daily candles?

## Data source

- Exchange: Kraken
- Pair: XBT/USD
- Interval: Daily
- Analysis observations: 30

## Summary

- First closing price in the period: $84,444.20
- Latest completed closing price: $80,001.90
- Closing-price change across the period: -5.26%
- Latest daily return: -0.06%
- Latest 7-day SMA: $81,454.71
- Latest 30-day SMA: $82,885.63
- Latest trend comparison: 7-day SMA below 30-day SMA
- Days flagged for unusual movement: 9
- Days flagged for high volume: 11

## Daily observations

| Date | Close (USD) | Return (%) | Volume (XBT) | 7-day SMA | 30-day SMA | Unusual move | High volume |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| 2026-09-27 | $84,444.20 | +0.02% | 1,317.7454 | $84,930.93 | $79,933.49 | No | No |
| 2026-09-28 | $83,462.70 | -1.16% | 3,143.1942 | $84,483.63 | $80,107.98 | No | Yes |
| 2026-09-29 | $83,633.40 | +0.20% | 2,167.1370 | $84,117.44 | $80,306.38 | No | No |
| 2026-09-30 | $83,564.70 | -0.08% | 2,715.9092 | $84,000.31 | $80,473.00 | No | Yes |
| 2026-10-01 | $84,849.10 | +1.54% | 3,339.2644 | $84,067.33 | $80,721.36 | Yes | Yes |
| 2026-10-02 | $84,503.70 | -0.41% | 5,170.8105 | $84,126.36 | $80,961.32 | No | Yes |
| 2026-10-03 | $84,740.00 | +0.28% | 772.6587 | $84,171.11 | $81,076.78 | No | No |
| 2026-10-04 | $86,510.40 | +2.09% | 993.8668 | $84,466.29 | $81,304.58 | Yes | No |
| 2026-10-05 | $85,751.50 | -0.88% | 2,531.7142 | $84,793.26 | $81,502.02 | No | Yes |
| 2026-10-06 | $85,542.10 | -0.24% | 2,145.3929 | $85,065.93 | $81,675.61 | No | No |
| 2026-10-07 | $83,276.10 | -2.65% | 3,278.1012 | $85,024.70 | $81,815.14 | Yes | Yes |
| 2026-10-08 | $81,683.80 | -1.91% | 4,015.1233 | $84,572.51 | $81,922.94 | Yes | Yes |
| 2026-10-09 | $82,559.40 | +1.07% | 1,778.0667 | $84,294.76 | $82,065.30 | Yes | No |
| 2026-10-10 | $82,912.70 | +0.43% | 490.3135 | $84,033.71 | $82,277.66 | No | No |
| 2026-10-11 | $83,675.60 | +0.92% | 853.1266 | $83,628.74 | $82,493.15 | No | No |
| 2026-10-12 | $81,737.10 | -2.32% | 2,372.6320 | $83,055.26 | $82,642.22 | Yes | No |
| 2026-10-13 | $83,101.20 | +1.67% | 2,895.4721 | $82,706.56 | $82,852.26 | Yes | Yes |
| 2026-10-14 | $81,576.40 | -1.83% | 2,598.8787 | $82,463.74 | $82,965.03 | Yes | No |
| 2026-10-15 | $82,133.70 | +0.68% | 3,383.7077 | $82,528.01 | $83,183.32 | No | Yes |
| 2026-10-16 | $81,500.80 | -0.77% | 2,089.3165 | $82,376.79 | $83,361.81 | No | No |
| 2026-10-17 | $81,382.00 | -0.15% | 599.4158 | $82,158.11 | $83,529.38 | No | No |
| 2026-10-18 | $82,001.70 | +0.76% | 987.1994 | $81,918.99 | $83,566.84 | No | No |
| 2026-10-19 | $81,843.70 | -0.19% | 1,935.3151 | $81,934.21 | $83,587.41 | No | No |
| 2026-10-20 | $82,936.10 | +1.33% | 2,159.9158 | $81,910.63 | $83,646.48 | No | No |
| 2026-10-21 | $84,022.50 | +1.31% | 2,408.7241 | $82,260.07 | $83,560.77 | No | No |
| 2026-10-22 | $81,315.90 | -3.22% | 2,762.2037 | $82,143.24 | $83,398.08 | Yes | Yes |
| 2026-10-23 | $81,086.20 | -0.28% | 1,328.9786 | $82,084.01 | $83,288.13 | No | No |
| 2026-10-24 | $80,771.90 | -0.39% | 1,924.8424 | $81,996.86 | $83,167.86 | No | No |
| 2026-10-25 | $80,048.50 | -0.90% | 894.4966 | $81,717.83 | $83,033.13 | No | No |
| 2026-10-26 | $80,001.90 | -0.06% | 2,534.8411 | $81,454.71 | $82,885.63 | No | Yes |

## Rule definitions

1. **Unusual movement:** Absolute daily return exceeds twice the median
   absolute daily return across the preceding 30 completed days.
2. **High volume:** Daily volume exceeds the average volume across the
   preceding 30 completed days.
3. **Trend comparison:** The 7-day SMA is compared with the 30-day SMA.

## Interpretation and limitations

These rules describe historical observations. They do not establish
causation, predict future prices, or provide buy/sell recommendations.
The analysis uses historical observations before the displayed 30-day period to calculate moving averages and rolling comparison thresholds.

## Educational disclaimer

This project is for education only and is not financial advice.
