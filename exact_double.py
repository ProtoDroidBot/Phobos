from decimal import Decimal, InvalidOperation
import math


def exact_double_text(value):
    """Return the complete decimal representation of a coordinate value.

    FSD vectors are stored as IEEE-754 doubles. Decimal.from_float exposes
    that double's exact value rather than Python's shorter display form.
    Existing decimal strings are kept as decimal values without routing them
    through float first.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            return None
        decimal_value = Decimal.from_float(value)
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, str):
        try:
            decimal_value = Decimal(value.strip())
        except InvalidOperation:
            return None
    else:
        try:
            float_value = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(float_value):
            return None
        decimal_value = Decimal.from_float(float_value)
    if not decimal_value.is_finite():
        return None
    return format(decimal_value, 'f')
