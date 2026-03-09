from datetime import datetime

from config import Config

class RentalPeriodExpiredError(Exception):
    
    def __init__(self, 
        current_end_date: datetime,
        now: datetime
        ):
    
        self.current_end_date = current_end_date
        self.now = now

        self.message = f"The rental period has already ended, therefore it cannot be modified. \
            Rental end date: {current_end_date.strftime(Config.time.timeformat)} current time: {now.strftime(Config.time.timeformat)}."
    
        super().__init__(self.message)
