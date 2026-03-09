class InsufficientQuantityError(Exception):
    
    def __init__(self, 
        available_quantity: float,
        new_quantity: float
        ):
        
        self.available_quantity = available_quantity
        
        self.new_quantity = new_quantity
        
        self.message = f"Not enough stock. Available: {available_quantity}, requested: {new_quantity}"
        
        super().__init__(self.message)
