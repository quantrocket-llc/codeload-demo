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

from zipline.api import (
    attach_pipeline,
    date_rules,
    order_target_percent,
    get_open_orders,
    cancel_order,
    pipeline_output,
    record,
    schedule_function,
    set_benchmark,
    symbol
)
from zipline.finance import commission
from zipline.pipeline import Pipeline
from zipline.pipeline.factors import CustomFactor
from zipline.pipeline.data import USEquityPricing

"""
Pipeline algorithm that buys recent winners and sells recent losers.

    Specifically:

    - rank stocks by their performance over the past MOMENTUM_WINDOW days
    - ignore very recent performance by excluding the last RANKING_PERIOD_GAP
    days from the ranking window (as commonly recommended for UMD)
    - buy the TOP_N_DECILES deciles of highest performing stocks and short the TOP_N_DECILES
    deciles of lowest performing stocks
    - rebalance the portfolio according to REBALANCE_INTERVAL
"""

MOMENTUM_WINDOW = 252
RANKING_PERIOD_GAP = 22
TOP_N_DECILES = 5
REBALANCE_INTERVAL = date_rules.month_start()

class Momentum(CustomFactor):
    """
    Calculates the percent change in close price over MOMENTUM_WINDOW,
    excluding the most recent RANKING_PERIOD_GAP periods.
    """
    inputs = [USEquityPricing.close]
    window_length = MOMENTUM_WINDOW

    def compute(self, today, assets, out, close):
        out[:] = (close[-RANKING_PERIOD_GAP] - close[0]) / close[0]


def make_pipeline():
    momentum = Momentum()
    return Pipeline(
        columns={
            'deciles': momentum.deciles()
        },
    )

def rebalance(context, data):

    # Pipeline data will be a dataframe with integer columns named 'deciles'
    pipeline_data = context.pipeline_data
    all_assets = pipeline_data.index

    longs = all_assets[pipeline_data.deciles >=  10 - TOP_N_DECILES]
    shorts = all_assets[pipeline_data.deciles < TOP_N_DECILES]

    universe_size = len(all_assets)
    positions_per_side = universe_size * TOP_N_DECILES/10
    position_size = 0.5 / positions_per_side

    record(universe_size=universe_size,
           positions_per_side=positions_per_side,
           position_size=position_size
           )

    # Build a 1x-leveraged, equal-weight, long-short portfolio.
    for asset in longs:
        for order in get_open_orders(asset):
            cancel_order(order)
        order_target_percent(asset, position_size)

    for asset in shorts:
        for order in get_open_orders(asset):
            cancel_order(order)
        order_target_percent(asset, -position_size)

    # Remove any assets that should no longer be in our portfolio.
    portfolio_assets = longs | shorts
    positions = context.portfolio.positions
    for asset in set(positions) - set(portfolio_assets):

        for order in get_open_orders(asset):
            cancel_order(order)

        if data.can_trade(asset):
            order_target_percent(asset, 0)


def initialize(context):
    attach_pipeline(make_pipeline(), 'my_pipeline')

    # If Zipline has trouble pulling the default benchmark, try setting the
    # benchmark to something already in your bundle
#    set_benchmark(symbol("change this to a symbol in your data"))

    # Rebalance periodically
    schedule_function(rebalance, REBALANCE_INTERVAL)

    context.set_commission(commission.PerShare(cost=.005, min_trade_cost=0))


def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')
