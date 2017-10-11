from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

# Import the backtrader platform
import backtrader as bt
import backtrader.feeds as btfeeds

from quantrocket.history import download_history_file

# Create a Stratey
class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Put files in /tmp to have QuantRocket automatically clean them out after
    # a few hours
    download_history_file(
        'orcl-eod-adj',
        filepath_or_buffer='/tmp/orcl-eod-adj.csv',
        fields=['ConId','Date','Open','Close','High','Low','Volume'])

    data = btfeeds.GenericCSVData(
        dataname='/tmp/orcl-eod-adj.csv',
        dtformat=('%Y-%m-%d'),
        datetime=1,
        open=2,
        close=3,
        high=4,
        low=5,
        volume=6
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
