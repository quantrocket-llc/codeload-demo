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

import backtrader as bt
import backtrader.feeds as btfeeds
from quantrocket.history import download_history_file

class DualMovingAverageStrategy(bt.SignalStrategy):

    params = (
        ('smavg_window', 100),
        ('lmavg_window', 300),
    )

    def __init__(self):

        # Compute long and short moving averages
        smavg = bt.ind.SMA(period=self.p.smavg_window)
        lmavg = bt.ind.SMA(period=self.p.lmavg_window)

        # Go long when short moving average is above long moving average
        self.signal_add(bt.SIGNAL_LONG, bt.ind.CrossOver(smavg, lmavg))

if __name__ == '__main__':

    cerebro = bt.Cerebro()

    # Create data feed using QuantRocket data and add to backtrader
    # (Put files in /tmp to have QuantRocket automatically clean them out after
    # a few hours)
    download_history_file(
        'aapl-1d',
        filepath_or_buffer='/tmp/aapl-1d.csv',
        fields=['ConId','Date','Open','Close','High','Low','Volume'])

    data = btfeeds.GenericCSVData(
        dataname='/tmp/aapl-1d.csv',
        dtformat=('%Y-%m-%d'),
        datetime=1,
        open=2,
        close=3,
        high=4,
        low=5,
        volume=6
    )
    cerebro.adddata(data)

    cerebro.addstrategy(DualMovingAverageStrategy)
    cerebro.run()

    # Save the plot to PDF so the satellite service can return it (make sure
    # to use the Agg backend)
    cerebro.plot(use='Agg', savefig=True, figfilename='/tmp/backtrader-plot.pdf')
