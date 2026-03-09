class InvalidDateFormatError(Exception):
    
    def __init__(self, 
        str_date: str
        ):
        
        self.str_date = str_date
        
        self.message = f"The following date: '{str_date}' does not match the expected format -> '%Y-%m-%d %H:%M:%S'"
        
        super().__init__(self.message)