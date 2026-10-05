// Shared design-system components and cross-app logic (auth session
// handling, login form) — see docs/architecture-blueprint.html §15.

export { AuthProvider, useAuth, api } from "./auth";
export { LoginForm } from "./LoginForm";
export { EyeIcon } from "./icons";
export type { LoginFormProps } from "./LoginForm";
export {
  EMPLOYEE_NUMBER_LENGTH,
  keepDigits,
  isValidEmployeeNumber,
  isValidEmail,
  PASSWORD_MIN_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_SPECIAL_CHARACTERS,
  PASSWORD_RULES,
  isPasswordValid,
  FULL_NAME_MIN_LENGTH,
  fullNameError,
  PHONE_MAX_LENGTH,
  isValidPhoneNumber,
} from "./validation";
export type { PasswordRule } from "./validation";
export { PieChart } from "./PieChart";
export type { PieSlice } from "./PieChart";
export { TrendChart } from "./TrendChart";
export type { TrendPoint } from "./TrendChart";
export { RankedBarChart } from "./RankedBarChart";
export type { BarDatum } from "./RankedBarChart";
