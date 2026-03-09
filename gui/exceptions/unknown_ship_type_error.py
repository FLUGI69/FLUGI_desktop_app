class UnknownShipTypeError(Exception):
    
    def __init__(self, type_name: str):
        
        self.type_name = type_name
        
        self.message = f"Unknown ship type encountered: '{type_name}'"
        
        super().__init__(self.message)