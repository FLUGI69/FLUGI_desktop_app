import math
import logging
import typing as t
from datetime import datetime, timezone
from dateutil import parser, tz
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP

from utils.logger import LoggerMixin
from utils.enums.quantity_range import QuantityRange
from config import Config

if t.TYPE_CHECKING:
    
    from async_loop.qt_app import QtApplication
 
class UtilityCalculator(LoggerMixin):
    
    log: logging.Logger
    
    def __init__(self,
        app: 'QtApplication'
        ):
    
        self.mnb_client = app.mnb_client
        
        # Fetch today's official exchange rates published by the MNB
        self.current_exchange_rates = self.mnb_client.get_current_exchange_rates()
        
        # Fetch the complete list of all currencies known/stored by the MNB system
        self.currencies = self.mnb_client.get_currencies()
        
        self.currencies_rates= [rate.currency for rate in self.current_exchange_rates.rates]
        
        self.available_currencies = [c for c in self.currencies if c in self.currencies_rates]
        
        self.current_date = datetime.now(Config.time.timezone_utc).date()
        
    def arithmetic_decimal(
        self,
        a: float | Decimal,
        b: float | Decimal,
        operation: str = "add",
        decimal_places: int = 4
        ) -> Decimal:
        """
        Performs a precise arithmetic operation on two numeric values using Decimal.

        Supports addition, subtraction, multiplication, and division,
        with exact Decimal precision and configurable rounding.

        Parameters
        ----------
        a : float or Decimal
            The first numeric value.
        b : float or Decimal
            The second numeric value.
        operation : str, optional
            The arithmetic operation to perform. Supported values:
            - "add"      → addition (a + b)
            - "subtract" → subtraction (a - b)
            - "multiply" → multiplication (a * b)
            - "divide"   → division (a / b)
            Defaults to "add".
        decimal_places : int, optional
            Number of decimal places to round the result to.
            Example: 2 → 0.00, 4 → 0.0000
            Defaults to 4.

        Returns
        -------
        Decimal
            The result of the arithmetic operation, rounded to the specified number of decimal places.

        Raises
        ------
        ValueError
            If an unsupported operation string is provided.
            If division by zero is attempted.

        Examples
        --------
        arithmetic_decimal(0.1234, 0.12, "add", 4)      -> Decimal('0.2434')
        arithmetic_decimal(0.1234, 0.12, "subtract", 4) -> Decimal('0.0034')
        arithmetic_decimal(1.5, 2, "multiply", 2)       -> Decimal('3.00')
        arithmetic_decimal(1.5, 2, "divide", 3)         -> Decimal('0.750')
        """

        a_dec = Decimal(str(a))
        b_dec = Decimal(str(b))
        
        if operation == "add":
            
            result = a_dec + b_dec
            
        elif operation == "subtract":
            
            result = a_dec - b_dec
            
        elif operation == "multiply":
            
            result = a_dec * b_dec
            
        elif operation == "divide":
            
            if b_dec == Decimal('0'):
                
                raise ValueError("Division by zero is not allowed")
            
            result = a_dec / b_dec
            
        else:
            
            raise ValueError("Unsupported operation '%s'. Supported: add, subtract, multiply, divide" % operation)
        
        rounding_pattern = "0." + "0" * decimal_places
        
        return result.quantize(Decimal(rounding_pattern), rounding = ROUND_HALF_UP)
    
    def parse_datetime_safe(self, date_str: str) -> datetime:
        """
        Input can be:
        - An ISO string with tzinfo
        - An ISO string without tzinfo
        - A datetime object

        Output: an aware datetime in UTC
        """
        if isinstance(date_str, datetime):
            
            dt = date_str
            
        else:
            
            dt = parser.isoparse(date_str)
            
        if dt.tzinfo is None:

            dt = dt.replace(tzinfo = tz.tzlocal())
        
        return dt.astimezone(timezone.utc)
    
    def check_quantity(self, quantity: float | Decimal) -> QuantityRange:
        """
        Determines the quantity range for the given value.

        Parameters:
            quantity (float or Decimal): The amount to check.

        Returns:
            QuantityRange: 
                - QuantityRange.ZERO_TO_THREE if the quantity is between 0 and 3 inclusive.
                - QuantityRange.THREE_TO_FIVE if the quantity is greater than 3 and up to 5 inclusive.
                - QuantityRange.ABOVE_FIVE if the quantity is greater than 5.
        
        Examples:
            check_quantity(2.5)    -> QuantityRange.ZERO_TO_THREE\n
            check_quantity(3)      -> QuantityRange.ZERO_TO_THREE\n
            check_quantity(3.5)    -> QuantityRange.THREE_TO_FIVE\n
            check_quantity(5)      -> QuantityRange.THREE_TO_FIVE\n
            check_quantity(5.1)    -> QuantityRange.ABOVE_FIVE\n
            check_quantity(-1)     -> raises ValueError
        """
        
        quantity = Decimal(quantity)
        
        if quantity < Decimal('0'):
            
            raise ValueError("Quantity cannot be negative")
        
        if Decimal('0') <= quantity <= Decimal('3'):
            
            return QuantityRange.ZERO_TO_THREE
        
        elif Decimal('3') < quantity <= Decimal('5'):
            
            return QuantityRange.THREE_TO_FIVE
        
        else:
            
            return QuantityRange.ABOVE_FIVE
        
    def is_zero(self, quantity: float | Decimal) -> bool:
        """
        Checks if the given quantity is exactly zero.
        
        Parameters:
            quantity (float or Decimal): the amount to check.
        
        Returns:
            bool: True if quantity is exactly 0, otherwise False.
        
        Examples:
            is_zero(0)        -> True\n
            is_zero(0.0)      -> True\n
            is_zero(0.0000)   -> True\n
            is_zero(0.0001)   -> False\n
            is_zero(0.1)      -> False\n
            is_zero(1)        -> False\n
        """
        return Decimal(quantity) == Decimal('0')

    def haversine_formula(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates the great-circle distance between two geographic points using the Haversine formula.
        This formula accounts for the Earth's curvature, providing an accurate distance along the sphere.

        Parameters:
            lat1, lon1: Latitude and longitude of the first point in degrees
            lat2, lon2: Latitude and longitude of the second point in degrees

        Returns:
            Distance along the Earth's surface in kilometers (float)
        """
        R = 6371  # Earth's radius in kilometers (R)
    
        phi1, phi2 = math.radians(lat1), math.radians(lat2) # φ1, φ2 = latitude of the two points in radians
        
        dphi = math.radians(lat2 - lat1) # Δφ = φ2 - φ1 (difference in latitude in radians)
        
        dlambda = math.radians(lon2 - lon1) # Δλ = λ2 - λ1 (difference in longitude in radians)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2 # Haversine formula: a = sin²(Δφ/2) + cos φ1 * cos φ2 * sin²(Δλ/2)
        
        return 2*R*math.asin(math.sqrt(a)) # Great-circle distance: d = 2 * R * arcsin(√a)
    
    def floats_are_equal(self, a: float, b: float) -> bool:
        """
        Determines whether two floating-point numbers are approximately equal,
        taking into account potential floating-point precision errors.

        Parameters
        ----------
        value1 : float
            The first number to compare.
        value2 : float
            The second number to compare.

        Returns
        -------
        bool
            True if the numbers are considered equal within a small tolerance, False otherwise.
        """
        self.log.debug("Comparing two float values: %s and %s for approximate equality" % (a, b))
        
        return math.isclose(a, b, rel_tol = 1e-9, abs_tol = 1e-12)

    def exchange_currency_to_huf(self, value: float, from_currency: str = "HUF") -> float:
        """
        Converts the specified amount from a given currency into Hungarian Forint (HUF)
        using the latest available MNB exchange rates.

        Notes
        -----
        - If `from_currency` is "HUF", the function returns the original value without conversion.
        - If a non-HUF currency is provided, the function looks up the corresponding
        MNB exchange rate and converts the value into HUF.
        - Raises a ValueError if the currency is not present in the current exchange rate list.

        Parameters
        ----------
        value : float
            The numeric amount that needs to be converted.
        from_currency : str, optional
            The currency code of the source value (e.g., "EUR", "USD").
            Defaults to "HUF".

        Returns
        -------
        float
            The converted amount in Hungarian Forint (HUF).
        """
        if from_currency != "HUF":
            
            if from_currency in self.available_currencies:
            
                self.log.debug("Exchange rates date: %s - current date (HU): %s" % (
                    self.current_exchange_rates.date, 
                    self.current_date
                    )
                )
                
                if self.current_exchange_rates.date != self.current_date:
                    
                    self.log.warning("The exchange rates retrieved are not for today")

                rate = next((rate for rate in self.current_exchange_rates.rates if rate.currency == from_currency), None)

                if rate is None:
                    
                    raise ValueError("Currency '%s' not found in exchange rates" % from_currency)
                    
                exchanged_value = value * float(rate.rate)
                
                self.log.debug("Converting %s %s -> %s HUF" % (value, from_currency, exchanged_value))
                
                return exchanged_value

            raise ValueError("Currency '%s' is not available in the current MNB currency list" % from_currency)
            
        return value
    
    def exchange_value(self, value: float, from_currency: str, to_currency: str) -> float:
        """
        Converts a monetary value from one currency to another using the latest
        MNB (Hungarian National Bank) exchange rates.

        Conversion logic
        ----------------
        - If `from_currency` is HUF, the value is divided by the target currency's
        exchange rate to obtain the foreign currency amount.
        - If `to_currency` is HUF, the value is multiplied by the source currency's
        exchange rate.
        - If both currencies are foreign (non-HUF), the conversion is performed via HUF:
            value -> HUF -> target currency.

        Parameters
        ----------
        value : float
            The numeric amount to convert.
        from_currency : str
            ISO currency code of the source value (e.g., "EUR", "USD", "HUF").
        to_currency : str
            ISO currency code of the target value (e.g., "EUR", "USD", "HUF").

        Returns
        -------
        float
            The converted value in the target currency.

        Raises
        ------
        ValueError
            If one or both currency codes are missing from the current MNB exchange rates.
        """
        if (from_currency and to_currency != "") and \
            (from_currency in self.available_currencies or to_currency in self.available_currencies):
            
            self.log.debug("Exchange rates date: %s - current date (HU): %s" % (
                self.current_exchange_rates.date, 
                self.current_date
                )
            )

            if self.current_exchange_rates.date != self.current_date:
                
                self.log.warning("The exchange rates retrieved are not for today")

            if from_currency == "HUF":
                
                to_rate = next((r for r in self.current_exchange_rates.rates if r.currency == to_currency), None)
                
                if to_rate is None:
                    
                    raise ValueError("To currency '%s' not found in exchange rates" % to_currency)
                
                exchanged = value / float(to_rate.rate)
                
                self.log.debug("Exchanging %s HUF -> %s %s" % (value, exchanged, to_currency))
                
                return exchanged

            if to_currency == "HUF":
                
                from_rate = next((r for r in self.current_exchange_rates.rates if r.currency == from_currency), None)
                
                if from_rate is None:
                    
                    raise ValueError("From currency '%s' not found in exchange rates" % from_currency)
            
                exchanged = value * float(from_rate.rate)
                
                self.log.debug("Exchanging %s %s -> %s HUF" % (value, from_currency, exchanged))
                
                return exchanged

            from_rate = next((r for r in self.current_exchange_rates.rates if r.currency == from_currency), None)
            
            to_rate = next((r for r in self.current_exchange_rates.rates if r.currency == to_currency), None)

            if from_rate is None:
                
                raise ValueError("From currency '%s' not found in exchange rates" % from_currency)

            if to_rate is None:
                
                raise ValueError("To currency '%s' not found in exchange rates" % to_currency)

            value_in_huf = value * float(from_rate.rate)
            
            exchanged = value_in_huf / float(to_rate.rate)
            
            self.log.debug("Exchanging %s %s -> %s %s via HUF (from_rate = %s, to_rate = %s)" %(
                value, 
                from_currency, 
                exchanged, 
                to_currency,
                from_rate.rate, 
                to_rate.rate
                )
            )

            return exchanged
        
        raise ValueError("Currency '%s' is not available in the current MNB currency list" % from_currency)