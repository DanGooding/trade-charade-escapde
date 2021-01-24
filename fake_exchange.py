
from collections import defaultdict
from optibook import InfoOnly


class FakeExchange:
    def __init__(self):
        self.e = InfoOnly() # can't make any trades
        self.cleared_bids = defaultdict(list)
        self.cleared_asks = defaultdict(list)
        self.pending_bids = defaultdict(list)
        self.pending_asks = defaultdict(list)
        
        self.positions = defaultdict(int)
        self.cash = 0
        
    def connect(self):
        self.e.connect()
    
    def disconnect(self):
        self.e.disconnect()
    
    def get_cash(self):
        return self.cash
    
    def get_positions(self):
        return self.positions
        
    def insert_order(self, instrument_id: str, price: float, volume: int, side: str, order_type: str = 'limit'):
        [price_book] = self.e.get_last_price_book(instrument_id)

        if side == 'bid':
            offers = price_book.asks
            acceptable_price = lambda p: price >= p
            cash_direction = -1
            other_cleared = self.cleared_asks[instrument_id]
            own_pending = self.pending_bids[instrument_id]
        
        elif side == 'ask':
            offers = price_book.bids
            acceptable_price = lambda p: price <= p
            cash_direction = 1
            other_cleared = self.cleared_bids[instrument_id]
            own_pending = self.pending_asks[instrument_id]
            
        else:
            ValueError('side must be bid or ask')
        
        
        i = 0
        while volume > 0 and i < len(offers):
            offer = offers[i]
            if not acceptable_price(offer.price):
                # cannot fulfil order
                break
                
            delta_volume = min(volume, offer.volume)
            self.cash += delta_volume * offer.price * cash_direction
            self.positions[instrument_id] -= delta_volume * cash_direction
            
            if volume >= offer.volume:
                # complete offer
                other_cleared.append(offer)
                volume -= delta_volume
            
            if volume <= offer.volume:
                # complete order
                offer.volume -= delta_volume  ## TODO
                return
            
            i += 1
        
        if volume > 0 and order_type == 'limit':
            # add this
            own_pending.append((volume, price))

    def get_outstanding_orders(self, instrument_id):
        
        # TODO do this properly
        return self.pending_asks[instrument_id] + self.pending_bids[instrument_id]
        
        
        