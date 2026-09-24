// Shared design-system components and cross-app logic (auth session
// handling, login form) — see docs/architecture-blueprint.html §15.

export { AuthProvider, useAuth, api } from "./auth";
export { LoginForm } from "./LoginForm";
export type { LoginFormProps } from "./LoginForm";
export {
  EMPLOYEE_NUMBER_LENGTH,
  keepDigits,
  isValidEmployeeNumber,
  PASSWORD_MIN_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_SPECIAL_CHARACTERS,
  PASSWORD_RULES,
  isPasswordValid,
} from "./validation";
export type { PasswordRule } from "./validation";
