# Proposal

## Research questions

Main question: Does the variability of trading activity predict lower returns in the cross-section of Binance USDT-margined perpetual futures (January 2020 – September 2026), and if so, why?

- RQ1: Do contracts with more variable trading activity earn lower subsequent returns than contracts with more stable trading activity?

- RQ2: Is the predictive power of a naive measure (the rolling standard deviation of hourly quote volume) explained by size and liquidity (proxied, for lack of market-cap data, by the level of dollar volume) and by newly listed contracts?

- RQ3: If we fix the signal (divide by the mean, i.e. use the coefficient of variation, and use daily volume over several months), does it still predict returns among coins of similar size, liquidity and age?

- RQ4: Is the effect concentrated in buyer-initiated trading activity, as a mispricing explanation would imply, or symmetric across buyer- and seller-initiated trading activity, as risk/liquidity explanations would imply?

## 1. Base factor & literature

**Puzzle**
It is well established that the level of liquidity is priced: less liquid stocks earn higher expected returns (Amihud and Mendelson, 1986). A natural extension is that the variability of liquidity should be priced as well: if investors dislike liquidity risk, stocks whose liquidity fluctuates more should earn higher returns as compensation.

Chordia, Subrahmanyam and Anshuman (2001) test this for NYSE and AMEX common stocks from 1966 to 1995 using monthly data. Because direct liquidity measures are not available over such a long period, they use trading activity (dollar trading volume and share turnover) as a proxy for liquidity, and measure its variability as the log coefficient of variation (standard deviation divided by mean) of the past 36 monthly values, ending in month t-2. Contrary to their hypothesis, stocks with more variable trading activity earn significantly lower subsequent returns.

In Fama-MacBeth regressions controlling for size, book-to-market, momentum, price, dividend yield and the level of trading activity, the coefficient on the variability of dollar volume is -0.333 (t = -5.10; Table 5). The result holds for Fama-French risk-adjusted returns and across many robustness checks, and a one-standard-deviation decrease in variability corresponds to roughly 150-200 basis points of extra return per year.

Importantly, the authors use the coefficient of variation rather than the standard deviation, because the standard deviation mainly reflects the level of trading volume (its correlation with log dollar volume is 0.908; Table 2): when the standard deviation is used instead, the level of dollar volume is no longer significant (footnote 6). The authors find no convincing explanation for this negative relation, which therefore remains a puzzle.

**Explanations from literatures**
Later papers offer two kinds of explanations, but there is no agreement on which one is right.

- *Risk-based, the low returns are a fair price, not a mistake.* Pereira and Zhang (2010) argue that investors can wait and trade when liquidity is good. Liquidity that moves around a lot is then useful to them, so they accept lower returns for it. Barinov (2015, working paper) argues that unstable trading activity is a sign of high firm-specific uncertainty. Such firms tend to hold up better when market-wide volatility rises, so investors accept lower returns for holding them. He finds that a market-volatility risk factor explains the effect, and he rejects both the liquidity-timing and the mispricing explanations for US stocks.

- *Mispricing: prices are temporarily too high.* This idea goes back to Miller (1977): when investors disagree and short selling is hard, prices follow the optimists, and the later low returns are prices coming back down. George and Hwang (2013, working paper) apply this idea to the puzzle and find support for it. Their evidence is strongest among stocks that few analysts follow and few institutions hold.

- *Related evidence.* Akbas, Armstrong and Petkova (2011, working paper) use a more direct liquidity measure: how much the price moves per dollar traded. When this measure is more volatile, returns are higher, as liquidity-risk theory predicts. This is the opposite of what Chordia et al. find for trading activity. So unstable trading activity is probably not the same thing as unstable liquidity.

**Crypto precedent**
Liu, Tsyvinski and Wu (2022) construct cryptocurrency counterparts of stock-market return predictors, using CoinMarketCap data for 2014-2018 at a weekly frequency. The standard deviation of dollar volume is among the characteristics with significant long-short returns (about -3.0% per week, top minus bottom quintile; Table 6 of the 2019 working-paper version), but it is explained by their three-factor model of cryptocurrency market, size and momentum. Notably, they use the standard deviation, which is the measure Chordia et al. avoided, and this may be why it is subsumed by size. Their sample consists of spot coins and predates the rise of perpetual futures, and the characteristics they examine (in the 2019 version) include no scale-free variability measure and no information on trade direction.

**Motivation & prior information**
I chose this signal because an initial practitioner backtest of a naive version (rolling standard deviation of hourly quote volume) looked strong. All results in this project come from my own code and data.

## 2. Diagnosis: what does the naive measure capture?

The naive measure is the rolling standard deviation of hourly quote volume over the past 63 hours, computed as in the original code (min_periods = 1, missing values set to zero). I replicate it with my own code and test three hypotheses about why it could appear to predict returns for reasons unrelated to the mechanism in Chordia et al. (2001). All diagnosis tests use the in-sample period (January 2020 – December 2024); return horizons and other test settings are fixed in Section 5.

**H1 - Size and liquidity.** Because the standard deviation scales with the level of trading volume, the naive measure may mainly capture size and liquidity (proxied by the level of dollar volume).  
*If this is true, we should see:*  
  (i) coins rank almost the same way on the naive measure and on dollar volume  
  (ii) the naive measure stops predicting returns once we compare coins with similar dollar volume, either by sorting coins into dollar-volume groups first (double sort) or by adding log dollar volume and its square to the Fama-MacBeth regressions.

**H2 - Horizon.** A 63-hour window is far shorter than the 36-month window in Chordia et al. At this horizon, the standard deviation of hourly volume is likely dominated by the intraday volume cycle (Asian, European and US trading hours) and short-lived spikes, rather than by the persistent variability of trading activity.  
*If this is true, we should see:* the naive measure ranks coins quite differently from a measure based on daily volume over several months, and the two relate to returns differently. I also show the average volume for each hour of the day, to show how large this daily rhythm is.

**H3 - New listings.** With min_periods = 1 and missing values set to zero, newly listed contracts receive extreme values computed from very few observations that are dominated by listing-day volume. New coins may also tend to fall after listing, like IPOs in stocks (Ritter, 1991).  
*If this is true, we should see:* coins listed less than 30 days ago show up far more often than they should in the top and bottom groups of the naive
measure, and the measure predicts returns much less well once these coins are removed or once the (log) time since listing is added to the regressions.

*Interpretation rule (fixed in advance).* If the naive measure's predictive power largely disappears under these checks, I conclude that it mainly reflects a disguised size/liquidity, horizon or new-listing effect. The purified measure in Section 3 is defined independently of these results.

## 3. Purified measure

For each coin and each day, I add up the 24 hourly quote volumes to get daily dollar volume.
The purified measure is the coefficient of variation of daily dollar volume over the past 90 days: the standard deviation divided by the mean, in logs, as in Chordia et al. A coin gets a value only if it has a full 90 days of data; I do not fill gaps with zeros.

The coefficient of variation can still be related to size, liquidity and age: small, illiquid or young coins trade more unevenly. So all tests also control for these. To check that 90 days is not a lucky choice, I also report results for 60 and 120 days. All choices are fixed here, before I look at any results.  

## 4. Mechanism test: buyers vs sellers

Binance reports, for every hour, how much volume came from buyers who traded immediately at the current price (taker buys). The rest came from sellers who did so. I add these up by day and compute the purified measure from Section 3 separately for each side: the variability of buyer-initiated volume and the variability of seller-initiated volume.

*Predictions*  

- If the effect comes from mispricing, it should come mainly from the buy side: bursts of eager buying push prices too high, and prices later fall back. Seller-initiated variability should matter less, or even point the other way, since bursts of selling may push prices too low.
- If the effect comes from risk or liquidity, the direction of trading should not matter and both sides should predict returns about equally well.

*Tests*  
(i) Compare how well each side predicts returns (rank IC and long-short returns).  
(ii) Put both sides into the same Fama-MacBeth regression, with the controls listed in Section 5, and test whether their coefficients differ.

*How I will read the results (fixed in advance)*  
A clearly stronger buy side supports the mispricing explanation. No clear difference is more in line with risk or liquidity explanations, but it may also mean the test is not sharp enough. A stronger sell side fits neither story, and I will report it as it is.

*Limitations*  
Taker buys are not only optimists: they also include short sellers buying back, some of them forced by liquidations. Forced buying can also push prices up for a while, so I control for recent returns (short-term reversal). Buy and sell volumes also move together closely, so the two measures will be highly correlated, which makes a difference harder to detect. I'll report this correlation.

## 5. Data and test design

**Data** Binance public data (data.binance.vision): hourly klines and funding rates for all 900 USDT-margined perpetual contracts listed at any time between January 2020 and September 2026, including contracts that were later delisted. The klines include open, high, low and close prices, volume, quote volume, number of trades and taker buy volume.

**Universe** Single-coin contracts only: I drop index contracts (such as BTCDOMUSDT), non-crypto contracts (such as stocks or gold) and stablecoins. The list of dropped contracts is saved with the code. The purified measure needs 90 days of history, so coins enter its tests after 90 days. The naive measure is tested twice: on all contracts, as in the original code, and on contracts with at least 90 days of history, to compare like with like.

**Timing and returns** Portfolios are formed once a week, on Monday at 00:00 UTC, using data up to the end of Sunday. To avoid bid-ask bounce, positions are entered one hour later, at the 01:00 UTC open price, and held for one week. Returns include funding: a long position pays the funding rate when it is positive and receives it when it is negative. If a contract is delisted during the week, I use its last available price. As a secondary check, I repeat the main tests with a one-day holding period.

**Controls**  

- Log dollar volume (average daily dollar volume over the past 90 days) and its square
- log days since listing
- momentum (return over the past 30 days, skipping the last day)
- short-term reversal (return over the last day)
- return volatility (standard deviation of daily returns over the past 30 days)
- the average funding rate over the past 7 days
Each week, all signals and controls are trimmed at the 1st and 99th percentiles and standardized across coins.  

**Tests**  

1. Rank IC: each week, the rank correlation between a signal and next week's returns
2. Quintile portfolios: each week, coins are split into five equal-weighted groups by the signal. I report each group's average return and the high-minus-low spread.
3. Fama-MacBeth regressions of next week's return on the signal and the controls.
4. Double sorts: coins are first split into three groups by dollar volume (or by age), then into three groups by the signal within each group.
5. Costs: the turnover of the high-minus-low portfolio, and its return after costs of 5 and 10 basis points per side.

All t-statistics use Newey-West standard errors with 4 lags. Because I run many tests, I treat |t| > 3 as strong evidence and |t| > 2 as weak evidence (Harvey, Liu and Zhu, 2016).

**Robustness** Windows of 60 and 120 days; dropping the smallest 20% of coins by dollar volume; results year by year.

**Sample split** In-sample: from the first week with enough data (April 2020) to December 2024. All development and all tests above use only this period. Out-of-sample: January 2025 to September 2026. I run it once, at the end, with the same code and settings, and report whatever comes out.

**What counts as success**  

- RQ2 (diagnosis) is judged by the predictions in Section 2.
- RQ1 and RQ3: the purified measure has a negative high-minus-low spread and a negative Fama-MacBeth coefficient after controls, with |t| > 2 in-sample, and the same sign out-of-sample.
- RQ4: the buy-side coefficient is more negative than the sell-side coefficient, with |t| > 2 for the difference.


## Deviations from the pre-registration

- 2026-10-26, start week: "the first week with enough data" is set to the first week in
  which at least 20 coins have the purified measure (18 May 2020), so that every week has
  enough coins for five groups. The 120-day robustness check uses the same rule for coins
  with 120 days of data (first week: 15 June 2020).
- 2026-10-26, log of the naive measure: the naive measure is a raw dollar amount and very
  skewed (average weekly skewness 9.2), so in a linear regression a few of the largest coins
  drive the slope. Chordia et al. take logs of their variability measures, and size is in
  logs too. I therefore add Fama-MacBeth regressions with log(naive). This was added after
  seeing that the raw version shows no relation in the regression; both versions are
  reported. Rank-based tests (rank IC, sorts) do not change with the log.

## Exploratory hypothesis (added 2026-10-27, after the in-sample results; not pre-registered)

In-sample, the purified measure predicts lower returns in ranks (rank IC < 0) but not in
average returns (quintile spread and Fama-MacBeth coefficient near zero), and the sign of the
average-return spread changes from year to year. A possible reason: coins with more variable
trading activity usually do worse, but a few of them rise sharply, which pulls their average
up. Two checks, fixed before looking at the out-of-sample data (`src/explore.py`):
(i) the spread of median returns between group 5 and group 1 is negative, with |t| > 2;
(ii) the share of coin-weeks with a return above +50% is higher in group 5 than in group 1.
I run them once out-of-sample, together with the pre-registered tests. Because the
hypothesis comes from the in-sample data, only the out-of-sample check counts as evidence.