from optibook.synchronous_client import Exchange
from strategy import Strategy
import time
import logging
logger = logging.getLogger('client')
logger.setLevel('INFO')
from collections import defaultdict, deque
import statistics

class DualHedgeStrat(Strategy):
    def __init__(self, exchange, hedge, instrument):
        super().__init__(exchange, [hedge, instrument])
        # only trade on one instrument
        self.instrument = instrument
        self.hedge = hedge

        self.wait_time = 5.0
        self.update_time = 0.1
        
        self.execution_time = time.time()
        self.quote_time = time.time()
        self.get_out_of_positions_time = time.time()
        self.prev_num_orders = 0
        
        self.id_bid = 0
        self.id_ask = 0
        self.lprice = 0
        self.hprice = 0
        
        self.hedge_vals = deque()
        self.avg_hedge = 0
    
    def get_price_spread(self, book):
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
        return ((ask_price + bid_price)/2, ask_price - bid_price)
    
    def quote_bid_ask(self):
        liquid_book = self.e.get_last_price_book(self.hedge)
        theo, spread = self.get_price_spread(liquid_book)  # was get_avg_price?
        
        liquid_l = theo - spread
        liquid_h = theo + spread
        
        observed, obs_spread = self.get_price_spread(self.e.get_last_price_book(self.instrument))
        obs_l = observed - obs_spread
        obs_h = observed + obs_spread
    
        self.lprice = obs_l
        self.hprice = obs_h
        
        delta = 0.45 * obs_spread
        # delta = self.avg_hedge*0.6
        
        our_bid = theo - delta
        our_ask = theo + delta
        
        self.id_bid = self.insert_order(self.instrument, price=our_bid, volume=1, side='bid', order_type='limit')
        self.id_ask = self.insert_order(self.instrument, price=our_ask, volume=1, side='ask', order_type='limit')
        #logger.info(f"Liquid: {liquid_l} to {liquid_h}, Illiquid: {liquid_l} to {obs_h}")
        # logger.info(f"Theoretical price: {theo} Spread: {spread}")
        # logger.info(f"Placed orders for {self.instrument} bid {our_bid} ask {our_ask}")
        # logger.info(f"Bid ID: {self.id_bid} Ask ID: {self.id_ask}")
        
    def run_hedge(self):
        orders = self.e.get_outstanding_orders(self.instrument)
        orders = list(orders)
        assert len(orders) == 1
        self.e.delete_orders(self.instrument)
        book = self.e.get_last_price_book(self.hedge)
        lowest_ask = book.asks[0].price-0.01 if len(book.asks) > 0 else 100000
        highest_bid = book.bids[0].price+0.01 if len(book.bids) > 0 else 1
        logger.info("Hedging")
        if orders[0] == self.id_bid: ## orders[0].side == 'bid'
            # need to place a bid
            self.insert_order(self.hedge, price=lowest_ask, volume=1, side='bid', order_type='ioc')
            logger.info(f"Placed hedge for {self.hedge} bid {lowest_ask} loss {lowest_ask - self.lprice}")
            hedge_amt = lowest_ask - self.lprice
        elif orders[0] == self.id_ask:
            # need to place an ask
            self.insert_order(self.hedge, price=highest_bid, volume=1, side='ask', order_type='ioc')
            logger.info(f"Placed hedge for {self.hedge} ask {highest_bid} loss {self.hprice - highest_bid}")
            hedge_amt = self.hprice - highest_bid
        else:
            raise ValueError("hedging on wrong order")
        if len(self.hedge_vals) == 10:
            self.hedge_vals.pop()
        self.hedge_vals.append(hedge_amt)
        self.avg_hedge = statistics.mean(self.hedge_vals)
    
    def update(self):
        num_orders = len(self.e.get_outstanding_orders(self.instrument))
        if num_orders == 0:
            logger.info("0 orders")
            self.quote_bid_ask()
            self.quote_time = time.time()
            self.log_pnl()
        elif num_orders == 1:
            if self.prev_num_orders != 1:
                self.execution_time = time.time()
            if time.time() - self.execution_time > self.wait_time:
                logger.info("1 order wait time exceeded")
                while len(self.e.get_outstanding_orders(self.instrument)) > 0:
                    self.run_hedge()
                    time.sleep(0.1)
                self.quote_bid_ask()
                self.quote_time = time.time()
                self.log_pnl()
                logger.info(f"Avg hedge loss: {self.avg_hedge}")
        elif num_orders == 2:
            if time.time() - self.quote_time > self.update_time:
                #logger.info("2 orders wait time exceeded")
                self.e.delete_orders(self.instrument)
                self.quote_bid_ask()
                self.quote_time = time.time()
                #self.log_pnl()
                #logger.info(f"Avg hedge loss: {self.avg_hedge}")
        else: 
            logger.error(f"{num_orders} orders")
            assert (1==0)
        self.prev_num_orders = num_orders
        
        worst_position = 0
        for s, p in self.e.get_positions().items():
            worst_position = max([worst_position, abs(p)])
        if worst_position > 50:
            self.get_out_of_positions()
