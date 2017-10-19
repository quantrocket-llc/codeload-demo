import numpy as np
import scipy as sp
from zipline.api import (
    continuous_future,
    schedule_function,
    date_rules,
    time_rules,
    record,
    order_target_percent,
    set_benchmark,
    set_commission,
    commission,
    set_slippage,
    slippage
)

def initialize(context):

    # Get continuous futures for Light Sweet Crude Oil...
    context.crude_oil = continuous_future('CL', roll='calendar')
    # ... and RBOB Gasoline
    context.gasoline = continuous_future('RB', roll='calendar')

    # If Zipline has trouble pulling the default benchmark, try setting the
    # benchmark to something already in your bundle
    set_benchmark(context.crude_oil)

    # Ignore commissions and slippage for now
    set_commission(us_futures=commission.PerTrade(cost=0))
    set_slippage(us_futures=slippage.FixedSlippage(spread=0.0))

    # Long and short moving average window lengths
    context.long_ma = 65
    context.short_ma = 5

    # True if we currently hold a long position on the spread
    context.currently_long_the_spread = False
    # True if we currently hold a short position on the spread
    context.currently_short_the_spread = False

    # Rebalance pairs every day, 30 minutes after market open
    schedule_function(func=rebalance_pairs,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open(minutes=30))

    # Record Crude Oil and Gasoline Futures prices everyday
    schedule_function(record_price,
                      date_rules.every_day(),
                      time_rules.market_open())

def rebalance_pairs(context, data):

    # Calculate how far away the current spread is from its equilibrium
    zscore = calc_spread_zscore(context, data)

    # Get target weights to rebalance portfolio
    target_weights = get_target_weights(context, data, zscore)

    if target_weights:
        # If we have target weights, rebalance portfolio
        cl_contract, rb_contract = data.current(
            [context.crude_oil, context.gasoline],
            'contract'
        )
        order_target_percent(cl_contract, target_weights[cl_contract])
        order_target_percent(rb_contract, target_weights[rb_contract])

def calc_spread_zscore(context, data):

    # Get pricing data for our pair of continuous futures
    prices = data.history([context.crude_oil,
                           context.gasoline],
                          'price',
                          context.long_ma,
                          '1d')

    cl_price = prices[context.crude_oil]
    rb_price = prices[context.gasoline]

    # Calculate returns for each continuous future
    cl_returns = cl_price.pct_change()[1:]
    rb_returns = rb_price.pct_change()[1:]

    # Calculate the spread
    regression = sp.stats.linregress(
        rb_returns[-context.long_ma:],
        cl_returns[-context.long_ma:],
    )
    spreads = cl_returns - (regression.slope * rb_returns)

    # Calculate zscore of current spread
    zscore = (np.mean(spreads[-context.short_ma]) - np.mean(spreads)) / np.std(spreads, ddof=1)

    return zscore

def get_target_weights(context, data, zscore):

    # Get current contracts for both continuous futures
    cl_contract, rb_contract = data.current(
        [context.crude_oil, context.gasoline],
        'contract'
    )

    # Initialize target weights
    target_weights = {}

    if context.currently_short_the_spread and zscore < 0.0:
        # Update target weights to exit position
        target_weights[cl_contract] = 0
        target_weights[rb_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif context.currently_long_the_spread and zscore > 0.0:
        # Update target weights to exit position
        target_weights[cl_contract] = 0
        target_weights[rb_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif zscore < -1.0 and (not context.currently_long_the_spread):
        # Update target weights to long the spread
        target_weights[cl_contract] = 0.5
        target_weights[rb_contract] = -0.5

        context.currently_long_the_spread = True
        context.currently_short_the_spread = False

    elif zscore > 1.0 and (not context.currently_short_the_spread):
        # Update target weights to short the spread
        target_weights[cl_contract] = -0.5
        target_weights[rb_contract] = 0.5

        context.currently_long_the_spread = False
        context.currently_short_the_spread = True

    return target_weights

def record_price(context, data):

    # Get current price of primary crude oil and gasoline contracts.
    crude_oil_price = data.current(context.crude_oil, 'price')
    gasoline_price = data.current(context.gasoline, 'price')

    # Adjust price of gasoline (42x) so that both futures have same scale.
    record(Crude_Oil=crude_oil_price, Gasoline=gasoline_price*42)
