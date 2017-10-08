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

class DualMovingAverageStrategy(Moonshot):

    CODE = "dma-tech"
    DB = "tech-giants-1d"
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
