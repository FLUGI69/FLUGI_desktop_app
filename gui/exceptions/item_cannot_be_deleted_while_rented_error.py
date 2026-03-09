class ItemCannotBeDeletedWhileRentedError(Exception):
    
    def __init__(self, 
        items: str
        ):
        
        self.items = items
        
        self.message = f"The following items: '{items}' cannot be deleted because it is currently rented."
        
        super().__init__(self.message)
