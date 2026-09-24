"""Account-provisioning rules shared by the UserCreate schema and the
create_admin bootstrap script, so the very first admin can't bypass the
same rules every other account is held to."""

import re

EMPLOYEE_NUMBER_PATTERN = re.compile(r"^\d{6}$")

SPECIAL_CHARACTERS = "!@#$%^&*"
_SPECIAL_PATTERN = re.compile(r"[!@#$%^&*]")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 12


def validate_employee_number(value: str) -> str:
    if not EMPLOYEE_NUMBER_PATTERN.fullmatch(value):
        raise ValueError("Employee number must be exactly 6 digits")
    return value


def validate_password_complexity(password: str) -> str:
    if not (PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH):
        raise ValueError(
            f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters long"
        )
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain a number")
    if not _SPECIAL_PATTERN.search(password):
        raise ValueError(f"Password must contain a special character ({SPECIAL_CHARACTERS})")
    return password
