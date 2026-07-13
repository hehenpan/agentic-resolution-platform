from loguru import logger

def parse_int_field(val: any, field_name: str, line_number: int) -> int:
    """
    Tries to convert the given value to an integer.
    Raises ValueError and logs an error message on failure.
    """
    try:
        return int(val)
    except (ValueError, TypeError) as exc:
        message = f"Invalid {field_name} '{val}' at line {line_number}."
        logger.error(message)
        raise ValueError(message) from exc


def parse_float_field(val: any, field_name: str, line_number: int) -> float:
    """
    Tries to convert the given value to a float.
    Raises ValueError and logs an error message on failure.
    """
    try:
        return float(val)
    except (ValueError, TypeError) as exc:
        message = f"Invalid {field_name} '{val}' at line {line_number}."
        logger.error(message)
        raise ValueError(message) from exc
