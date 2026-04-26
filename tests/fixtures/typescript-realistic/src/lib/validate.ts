// Input validation utilities.
import { ValidationError } from "@/lib/errors";

type FieldErrors = Record<string, string>;

export function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function validateRequired(value: unknown, fieldName: string): void {
  if (value === null || value === undefined || value === "") {
    throw new ValidationError(`${fieldName} is required`, { [fieldName]: "required" });
  }
}

export function validateLength(
  value: string,
  fieldName: string,
  min: number,
  max: number,
): void {
  if (value.length < min || value.length > max) {
    throw new ValidationError(
      `${fieldName} must be between ${min} and ${max} characters`,
      { [fieldName]: `length must be ${min}–${max}` },
    );
  }
}

export function validateUserInput(input: {
  email?: string;
  name?: string;
  password?: string;
}): FieldErrors {
  const errors: FieldErrors = {};

  if (input.email !== undefined && !validateEmail(input.email)) {
    errors.email = "Invalid email format";
  }

  if (input.name !== undefined && (input.name.length < 2 || input.name.length > 100)) {
    errors.name = "Name must be 2–100 characters";
  }

  if (input.password !== undefined && input.password.length < 8) {
    errors.password = "Password must be at least 8 characters";
  }

  return errors;
}

export function assertNoErrors(errors: FieldErrors): void {
  if (Object.keys(errors).length > 0) {
    throw new ValidationError("Validation failed", errors);
  }
}
