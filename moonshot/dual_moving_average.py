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
from moonshot.commission import FuturesCommission

class DualMovingAverageStrategy(Moonshot):

    CODE = "dma"
    LMAVG_WINDOW = 300
    SMAVG_WINDOW = 100

    def get_signals(self, prices):
        closes = prices.loc["Close"]

        # Compute long and short moving averages
        lmavgs = closes.rolling(self.LMAVG_WINDOW).mean()
        smavgs = closes.rolling(self.SMAVG_WINDOW).mean()

        # Go long when short moving average is above long moving average
        signals = smavgs.shift() > lmavgs.shift()

        return signals.astype(int)

    def allocate_weights(self, signals, prices):
        # spread our capital equally among our trades on any given day
        weights = self.allocate_equal_weights(signals) # provided by moonshot.mixins.WeightAllocationMixin
        return weights

    def simulate_positions(self, weights, prices):
        # we'll enter in the period after the signal
        positions = weights.shift()
        return positions

    def simulate_gross_returns(self, positions, prices):
        # Our return is the security's close-to-close return, multiplied by
        # the size of our position. We must shift the positions DataFrame because
        # we don't have a return until the period after we open the position
        closes = prices.loc["Close"]
        gross_returns = closes.pct_change() * positions.shift()
        return gross_returns

class GlobexEquityEMiniFixedCommission(FuturesCommission):

    IB_COMMISSION_PER_CONTRACT = 0.85
    EXCHANGE_FEE_PER_CONTRACT = 1.18
    CARRYING_FEE_PER_CONTRACT = 0 # Depends on equity in excess of margin requirement

class DualMovingAverageFuturesStrategy(DualMovingAverageStrategy):

    CODE = "dma-fut"
    DB = "demo-fut-1min"
    LMAVG_WINDOW = 200
    SMAVG_WINDOW = 50
    CONT_FUT = "concat"
    COMMISSION_CLASS = GlobexEquityEMiniFixedCommission

class DualMovingAverageTechGiantsStrategy(DualMovingAverageStrategy):

    CODE = "dma-tech"
    DB = "tech-giants-1d"
    LMAVG_WINDOW = 300
    SMAVG_WINDOW = 100

class DualMovingAverageETFStrategy(DualMovingAverageStrategy):

    CODE = "dma-etf"
    DB = "etf-sampler-1d"
    LMAVG_WINDOW = 300
    SMAVG_WINDOW = 100
    BENCHMARK = 756733
