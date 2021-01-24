from optibook.synchronous_client import Exchange
from strategy import Strategy
import time
import logging
logger = logging.getLogger('client')
logger.setLevel('INFO')
from collections import defaultdict

class DualPaperStrat(Strategy):
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        # only trade on one instrument
        # self.instrument = self.instruments[0]
        # self.instruments = [self.instruments[1]]
        self.wait_time = 5.0
        self.update_time = 1.0
        
        self.execution_time = {i: time.time() for i in instruments}
        self.quote_time = {i: time.time() for i in instruments}
        self.prev_num_orders = defaultdict(int)
    
    def quote_bid_ask(self, instrument):
        book = self.e.get_last_price_book(instrument)
        asks = book.asks
        bids = book.bids
        if len(book.asks) == 0 and len(book.bids) == 0:
            ask_price = 0
            bid_price = 0
        elif len(book.asks) == 0:
            bid_price = book.bids[0].price
            ask_price = bid_price
        elif len(book.bids) == 0:
            ask_price = book.asks[0].price
            bid_price = ask_price
        else:
            ask_price = book.asks[0].price
            bid_price = book.bids[0].price
        
        difference = ask_price - bid_price
        gap = 0.02
        delta = difference / 2 - 0.02
        # delta = 0.3 * difference
        
        our_bid = bid_price + delta
        our_ask = ask_price - delta
        
        self.insert_order(instrument, price=our_bid, volume=1, side='bid', order_type='limit')
        self.insert_order(instrument, price=our_ask, volume=1, side='ask', order_type='limit')
        logger.info(f"Placed orders for {instrument} bid {our_bid} ask {our_ask}")
        
    def update(self):
        for instrument in self.instruments:
            num_orders = len(self.e.get_outstanding_orders(instrument))
            t = time.time()
            if num_orders == 0:
                logger.info("0 orders")
                self.quote_bid_ask(instrument)
                self.quote_time[instrument] = t
            elif num_orders == 1:
                if self.prev_num_orders[instrument] != 1:
                    self.execution_time[instrument] = t
                if t - self.execution_time[instrument] > self.wait_time:
                    logger.info("1 order wait time exceeded")
                    # self.e.delete_orders(instrument)
                    self.get_out_of_positions(target=30, instrument=instrument)
                    self.quote_bid_ask(instrument)
                    self.quote_time[instrument] = t
            else:
                if t - self.quote_time[instrument] > self.update_time:
                    logger.info("2 orders wait time exceeded")
                    self.e.delete_orders(instrument)
                    self.quote_bid_ask(instrument)
                    self.quote_time[instrument] = t
            self.prev_num_orders[instrument] = num_orders
