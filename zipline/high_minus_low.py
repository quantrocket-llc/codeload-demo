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

"""
Pipeline algorithm that longs the top 3 value stocks (= low price-to-book
ratio) and shorts the top 3 growth stocks (= high price-to-book ratio) using
Reuters financials
"""

from six import viewkeys
from zipline.api import (
    attach_pipeline,
    date_rules,
    order_target_percent,
    pipeline_output,
    record,
    schedule_function,
    set_benchmark,
    symbol
)
from zipline.finance import commission
from zipline.pipeline import Pipeline, CustomFactor
from zipline.pipeline.data import USEquityPricing
# Import ReutersFinancials pipeline data (ReutersInterimFinancials is also
# available)
from zipline_extensions.pipeline.data import ReutersFinancials

# Create a price-to-book custom pipeline factor
class PriceBookRatio(CustomFactor):
    """
    Calculate book value per share, defined as:

        (Total Assets - Total Liabilities) / Number of shares outstanding

    The COA codes we'll use for these metrics are 'ATOT' (Total Assets),
    'LTLL' (Total Liabilities), and 'QTCO' (Total Common Shares Outstanding).

    """
    inputs = [
        USEquityPricing.close,
        ReutersFinancials.ATOT, # total assets
        ReutersFinancials.LTLL, # total liabilities
        ReutersFinancials.QTCO] # common shares outstanding
    window_length = 1

    def compute(self, today, assets, out, closes, tot_assets, tot_liabilities, shares_out):
        book_values_per_share = (tot_assets - tot_liabilities)/shares_out
        pb_ratios = closes/book_values_per_share
        out[:] = pb_ratios

def rebalance(context, data):

    pipeline_data = context.pipeline_data
    all_assets = pipeline_data.index

    # Sort by P/B ratio
    assets_by_pb_ratio = pipeline_data.sort_values('pb_ratio', ascending=True)

    # Remove nulls
    assets_by_pb_ratio = assets_by_pb_ratio.loc[assets_by_pb_ratio.pb_ratio.notnull()]

    # If we don't have enough data for a complete portfolio, do nothing
    if len(assets_by_pb_ratio) < 6:
        return

    longs = assets_by_pb_ratio.index[:3]
    shorts = assets_by_pb_ratio.index[-3:]

    # Build a 1x-leveraged, equal-weight, long-short portfolio.
    allocation_per_asset = 1.0 / 6.0
    for asset in longs:
        order_target_percent(asset, allocation_per_asset)

    for asset in shorts:
        order_target_percent(asset, -allocation_per_asset)

    # Remove any assets that should no longer be in our portfolio.
    portfolio_assets = longs | shorts
    positions = context.portfolio.positions
    exit_positions = viewkeys(positions) - set(portfolio_assets)

    # TODO
    # There's a bug somewhere as Zipline is not exiting the positions when
    # told so the number of holdings increases over time

    record(num_positions=len(positions),
           existing_positions=",".join([str(p) for p in positions]),
           desired_positions=",".join([str(p) for p in portfolio_assets]),
           exit_positions=",".join([str(p) for p in exit_positions]))

    for asset in exit_positions:
        order_target_percent(asset, 0)

def initialize(context):
    pipe = Pipeline()
    attach_pipeline(pipe, 'my_pipeline')

    pb_ratios = PriceBookRatio()
    pipe.add(pb_ratios, 'pb_ratio')

    # If Zipline has trouble pulling the default benchmark, try setting the
    # benchmark to something already in your bundle
    set_benchmark(symbol("change this to a symbol in your data (or remove to make Zipline download SPY)"))

    # Rebalance monthly
    schedule_function(rebalance, date_rules.month_start())

    context.set_commission(commission.PerShare(cost=.0075, min_trade_cost=1.0))

def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')
