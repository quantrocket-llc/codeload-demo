#!/usr/bin/env python
#
# Copyright 2017 QuantRocket LLC
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
Dual moving average crossover algorithm demonstrating the use of futures in
Zipline.

Buy a futures contract when the short moving average is above its long moving
average and sell when the short moving average is below the long moving
average.
"""

from zipline.api import (
    continuous_future,
    order_target_percent,
    record,
    commission,
    slippage,
    set_commission,
    set_slippage,
    get_open_orders,
    cancel_order
)

def initialize(context):
    context.fut = continuous_future('ES', roll='calendar')

    # Ignore commissions and slippage for now
    set_commission(us_futures=commission.PerTrade(cost=0))
    set_slippage(us_futures=slippage.FixedSlippage(spread=0.0))

    context.i = 0
    context.invested = False

def handle_data(context, data):

    # Skip first 200 periods to get full windows
    context.i += 1
    if context.i < 200:
        return

    # Calculate moving averages
    short_mavg = data.history(context.fut, 'price', 50, '1m').mean()
    long_mavg = data.history(context.fut, 'price', 200, '1m').mean()

    # Enter the long position
    if short_mavg > long_mavg and not context.invested:

        fut_contract = data.current(context.fut, 'contract')

        # cancel open orders for contract, if any
        for order in get_open_orders(fut_contract):
            cancel_order(order)

        order_target_percent(fut_contract, 1)
        context.invested = True

    # Exit the long position
    elif short_mavg < long_mavg and context.invested:

        # cancel any open orders
        for order in get_open_orders():
            cancel_order(order)

        positions = context.portfolio.positions
        for asset in positions:
            order_target_percent(asset, 0)

        context.invested = False

    # Save values for later inspection
    record(current_price=data.current(context.fut, "price"),
           short_mavg=short_mavg,
           long_mavg=long_mavg)
