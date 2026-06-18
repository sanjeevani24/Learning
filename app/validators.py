import re

def validate_pan(pan: str) -> bool:
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    return bool(re.match(pattern, pan))


def validate_aadhaar(aadhaar: str) -> bool:

    if not aadhaar.isdigit():
        return False

    if len(aadhaar) != 12:
        return False

    if aadhaar[0] in ["0", "1"]:
        return False

    return True

