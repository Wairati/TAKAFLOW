// Mirrors backend/app/core/validation.py — keep both in sync if either changes.

export const EMPLOYEE_NUMBER_LENGTH = 6;

/** Strips anything that isn't a digit — used to filter employee-number input as the user types. */
export function keepDigits(value: string): string {
  return value.replace(/\D/g, "");
}

export function isValidEmployeeNumber(value: string): boolean {
  return new RegExp(`^\\d{${EMPLOYEE_NUMBER_LENGTH}}$`).test(value);
}

export const PHONE_MAX_LENGTH = 10;

export function isValidPhoneNumber(value: string): boolean {
  return value.length > 0 && value.length <= PHONE_MAX_LENGTH && !/\D/.test(value);
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

export const FULL_NAME_MIN_LENGTH = 2;

/** Returns a specific reason the name is invalid, or null if it's fine —
 * mirrors backend/app/core/validation.py's validate_full_name exactly. */
export function fullNameError(value: string): string | null {
  const trimmed = value.trim();
  if (trimmed.length < FULL_NAME_MIN_LENGTH) {
    return `Full name must be at least ${FULL_NAME_MIN_LENGTH} characters.`;
  }
  if (/\d/.test(trimmed)) {
    return "Full name cannot contain numbers.";
  }
  if (!/\p{L}/u.test(trimmed)) {
    return "Full name must contain at least one letter.";
  }
  return null;
}

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 12;
export const PASSWORD_SPECIAL_CHARACTERS = "!@#$%^&*";

export interface PasswordRule {
  label: string;
  test: (password: string) => boolean;
}

export const PASSWORD_RULES: PasswordRule[] = [
  {
    label: `${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} characters`,
    test: (pw) => pw.length >= PASSWORD_MIN_LENGTH && pw.length <= PASSWORD_MAX_LENGTH,
  },
  { label: "An uppercase letter (A-Z)", test: (pw) => /[A-Z]/.test(pw) },
  { label: "A lowercase letter (a-z)", test: (pw) => /[a-z]/.test(pw) },
  { label: "A number (0-9)", test: (pw) => /[0-9]/.test(pw) },
  {
    label: `A special character (${PASSWORD_SPECIAL_CHARACTERS})`,
    test: (pw) => /[!@#$%^&*]/.test(pw),
  },
];

export function isPasswordValid(password: string): boolean {
  return PASSWORD_RULES.every((rule) => rule.test(password));
}
