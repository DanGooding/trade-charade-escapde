from strategy import Strategy


class ExtremesStrategy(Strategy):
    """ places one very high ask and one very low bid, on the off chance someone accidentally does it """
    
    def __init__(self, exchange, instruments):
        super().__init__(exchange, instruments)
        
        self.placed = False
    
    
    def update(self):
        if not self.placed:
            
            for instrument_id in self.instruments:
                self.e.insert_order(instrument_id, price=1000, volume=1, side='ask', order_type='limit')
                self.e.insert_order(instrument_id, price=10, volume=1, side='bid', order_type='limit')
            
            self.placed = True

