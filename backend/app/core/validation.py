"""Account-provisioning rules shared by the UserCreate schema and the
create_admin bootstrap script, so the very first admin can't bypass the
same rules every other account is held to."""

import re

EMPLOYEE_NUMBER_PATTERN = re.compile(r"^\d{6}$")

PHONE_MAX_LENGTH = 10
_PHONE_NON_DIGIT = re.compile(r"\D")

_FULL_NAME_HAS_DIGIT = re.compile(r"\d")
_FULL_NAME_HAS_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)
FULL_NAME_MIN_LENGTH = 2

SPECIAL_CHARACTERS = "!@#$%^&*"
_SPECIAL_PATTERN = re.compile(r"[!@#$%^&*]")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 12


def validate_employee_number(value: str) -> str:
    if not EMPLOYEE_NUMBER_PATTERN.fullmatch(value):
        raise ValueError("Employee number must be exactly 6 digits")
    return value


def validate_phone_number(value: str) -> str:
    if _PHONE_NON_DIGIT.search(value):
        raise ValueError("Phone number can only contain digits")
    if len(value) > PHONE_MAX_LENGTH:
        raise ValueError(f"Phone number must not be more than {PHONE_MAX_LENGTH} digits")
    return value


def validate_full_name(value: str) -> str:
    stripped = value.strip()
    if len(stripped) < FULL_NAME_MIN_LENGTH:
        raise ValueError(f"Full name must be at least {FULL_NAME_MIN_LENGTH} characters")
    if _FULL_NAME_HAS_DIGIT.search(stripped):
        raise ValueError("Full name cannot contain numbers")
    if not _FULL_NAME_HAS_LETTER.search(stripped):
        raise ValueError("Full name must contain at least one letter")
    return stripped


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
