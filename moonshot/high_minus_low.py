# Copyright 2017 QuantRocket LLC - All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from moonshot import Moonshot
from moonshot.commission import PerShareCommission

class HighMinusLow(Moonshot):
    """
    Strategy that buys stocks with high book-to-market ratios and shorts
    stocks with low book-to-market ratios.

    Specifically:

    - calculate book value per share
    - rank securities by price-to-book ratio
    - buy the TOP_N_PCT percent of stocks with the lowest P/B ratios and short the TOP_N_PCT
    percent of stocks with the highest P/B ratios
    - rebalance the portfolio according to REBALANCE_INTERVAL
    """

    CODE = "hml"
    TOP_N_PCT = 10 # Buy/sell the bottom/top decile
    REBALANCE_INTERVAL = "M" # M = monthly; see http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases

    def get_signals(self, prices):

        # calculate book value per share, defined as:
        #
        #    (Total Assets - Total Liabilities) / Number of shares outstanding
        #
        # The COA codes for these metrics are 'ATOT' (Total Assets), 'LTLL' (Total
        # Liabilities), and 'QTCO' (Total Common Shares Outstanding).

        closes = prices.loc["Close"]
        financials = self.get_reuters_financials(["ATOT", "LTLL", "QTCO"], reindex_like=closes)
        tot_assets = financials.loc["ATOT"].loc["Amount"]
        tot_liabilities = financials.loc["LTLL"].loc["Amount"]
        shares_out = financials.loc["QTCO"].loc["Amount"]
        book_values_per_share = (tot_assets - tot_liabilities)/shares_out

        # Calculate and rank by price-to-book ratio
        pb_ratios = closes/book_values_per_share
        highest_pb_ratio_ranks = pb_ratios.rank(axis=1, ascending=False, pct=True)
        lowest_pb_ratio_ranks = pb_ratios.rank(axis=1, ascending=True, pct=True)

        top_n_pct = self.TOP_N_PCT / 100

        # Get long and short signals and convert to 1, 0, -1
        longs = (lowest_pb_ratio_ranks <= top_n_pct)
        shorts = (highest_pb_ratio_ranks <= top_n_pct)

        longs = longs.astype(int)
        shorts = -shorts.astype(int)

        # Combine long and short signals
        signals = longs.where(longs == 1, shorts)

        # Resample using the rebalancing interval.
        # Keep only the last signal of the month, then fill it forward
        signals = signals.resample(self.REBALANCE_INTERVAL).last()
        signals = signals.reindex(closes.index, method="ffill")

        return signals

    def allocate_weights(self, signals, prices):
        weights = self.allocate_equal_weights(signals)
        return weights

    def simulate_positions(self, weights, prices):
        # Enter the position in the period/day after the signal
        return weights.shift()

    def simulate_gross_returns(self, positions, prices):
        # We'll enter on the open, so our return is today's open to
        # tomorrow's open
        opens = prices.loc["Open"]
        gross_returns = opens.pct_change() * positions.shift()
        return gross_returns

class USStockCommission(PerShareCommission):
    IB_COMMISSION_PER_SHARE = 0.005

class HighMinusLowAmex(HighMinusLow):

    CODE = "hml-amex"
    DB = "amex-1d"
    COMMISSION_CLASS = USStockCommission
