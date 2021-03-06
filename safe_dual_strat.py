from optibook.synchronous_client import Exchange
import time
from enum import Enum
import logging
from strategy import Strategy
logger = logging.getLogger('client')
logger.setLevel('INFO')

class State(Enum):
    CHECK_MARKETS = 0
    WAIT_FOR_ORDER_COMPLETE = 1
    UNFULFILLED_ORDER_DELAY = 2

# Simultaneously submit IOC orders across instruments to capitalize on price differences between them.
# (When I1.ask < I2.bid, take I1.ask and sell back to I2.bid)
#   This "safe" version will wait some time if an order fails,
#   and will prevent positions from becoming too extreme on either instrument by taking non-profit trades across instruments.
class SafeDualStrat(Strategy):
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        self.state = State.CHECK_MARKETS
        self.changed_at = time.time()
        self.orders = {}
        # Start correcting position if max(abs(instrument.position)) >= start_correcting_at
        self.correcting_position = False
        self.start_correcting_at = 20
        self.stop_correcting_at = 5
        # RISK: The greater we trade in single orders, the greater the penalty for missing an order
        # Solution: cap single order volume
        #   - This should be no more than the position extremity limit, to avoid jumping between extremes.
        #   - (Tradeoff - sacrifice some profit but reduce risk of order failure & extremity of position imbalance).
        self.max_single_order_volume = max([20, self.start_correcting_at])
        # RISK: We lose money when one of our orders gets fulfilled and the other doesn't.
        # Solution: if an order takes too long to complete, stop and wait some time for market to settle
        #   - (Tradeoff - longer waiting times reduce risk of successive order fails but decrease productivity)
        self.order_escape_time = 1 # Max time between posting an order and it being completed
        self.post_escape_recovery_time = 5 # Min time between getting out of an order and posting a new one
    
        self.check_position_extremity()
    
    def update(self):
        t = time.time()
        
        if self.state == State.CHECK_MARKETS:
            if self.check_for_discrepancies():
                self.change_state(State.WAIT_FOR_ORDER_COMPLETE)
        elif self.state == State.WAIT_FOR_ORDER_COMPLETE:
            if self.orders_complete():
                logger.info("Orders complete")
                self.check_position_extremity()
                self.state = State.CHECK_MARKETS
            elif t - self.changed_at >= self.order_escape_time:
                logger.info("DUAL ORDER FAILED - escaping")
                self.get_out_of_positions(450)
                self.check_position_extremity()
                self.change_state(State.UNFULFILLED_ORDER_DELAY)
        else: 
            if t - self.changed_at >= self.post_escape_recovery_time:
                self.change_state(State.CHECK_MARKETS)
    
    def orders_complete(self):
        outstanding = {}
        for i in self.instruments:
            for order in self.e.get_outstanding_orders(i):
                if order in self.orders:
                    outstanding[order]=self.orders[order]
        self.orders = outstanding
        return len(outstanding)==0
    
    def change_state(self, newstate):
        self.state = newstate
        self.changed_at = time.time()
    
    # LIMIT: Total position (positive or negative) per instrument cannot go over 500.
    # Solution: Check the extemity of our positions and enter "correction" mode if above threshold
    # - Start correcting position when most extreme position is above self.start_correcting_at...
    # - Don't stop correcting our position until most extreme is below self.stop_correcting_at
    def check_position_extremity(self):
        worst_position = 0
        for s, p in self.e.get_positions().items():
            worst_position = max([worst_position, abs(p)])
        if self.correcting_position and worst_position <= self.stop_correcting_at:
            print(f"Our position is balanced enough now (abs(p)={p}), going back to making profit.")
            self.correcting_position = False 
        elif (not self.correcting_position) and worst_position >= self.start_correcting_at:
            print(f"EXTREME position (abs(p)={worst_position}), seeking dual trades that can correct it.")
            self.correcting_position = True
        else:
            print(f"(Keeping current correction/profit behaviour... (abs(p)={worst_position}))")
        
    def check_for_discrepancies(self):
        # Compare prices across both instruments
        # - Could be extended to iterate over all instrument pairs given more listings
        books = [self.e.get_last_price_book(x) for x in self.instruments]
        for m1, m2 in [(0,1), (1,0)]:
            m1_id = self.instruments[m1]
            m2_id = self.instruments[m2]
            try:
                m1_ask = books[m1].asks[0]
                m2_bid = books[m2].bids[0]
                vol = min([m1_ask.volume, m2_bid.volume, self.max_single_order_volume])
                
                # If we're trying to correct our position, don't make orders that make our position more extreme
                if(self.correcting_position):
                    if (self.e.get_positions()[m1_id] < self.stop_correcting_at and m1_ask.price <= m2_bid.price):
                        delta = (m2_bid.price - m1_ask.price) * 0.2
                        self.orders[self.e.insert_order(m1_id, price=m1_ask.price + delta, volume=vol, side='bid', order_type='limit')]=(m1_id, 'bid')
                        self.orders[self.e.insert_order(m2_id, price=m2_bid.price - delta, volume=vol, side='ask', order_type='limit')]=(m2_id, 'ask')
                        logger.info(f"Can correct position: buy {m1_id} at {m1_ask} and sell {m2_id} at {m2_bid}")
                        return True
                # If we aren't trying to correct position, just make orders that are profitable
                elif m1_ask.price < m2_bid.price:
                    delta = (m2_bid.price - m1_ask.price) * 0.2
                    self.orders[self.e.insert_order(m1_id, price=m1_ask.price + delta, volume=vol, side='bid', order_type='limit')]=(m1_id, 'bid')
                    self.orders[self.e.insert_order(m2_id, price=m2_bid.price - delta, volume=vol, side='ask', order_type='limit')]=(m2_id, 'ask')
                    logger.info(f"Can profit: buy {m1_id} at {m1_ask} and sell {m2_id} at {m2_bid}")
                    return True
            except Exception as e:
                # logger.info(e)
                continue
        return False
