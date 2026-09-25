import { clsx } from "clsx";
import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

// Every field gets an explicit background/foreground/border — never
// "transparent" or a browser default — so it can never blend into a
// differently-themed ancestor (see ARCHITECTURE.md Design System audit).
const fieldBase =
  "w-full rounded-lg border border-border bg-surface text-foreground px-3 py-2 text-sm outline-none transition-colors focus:border-brand-600 focus:ring-1 focus:ring-brand-600 disabled:bg-surface-muted disabled:text-foreground-muted disabled:opacity-100";

interface FieldWrapperProps {
  label?: string;
  error?: string;
  hint?: string;
  htmlFor?: string;
}

function FieldWrapper({ label, error, hint, htmlFor, children }: FieldWrapperProps & { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={htmlFor} className="text-sm font-medium">
          {label}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-foreground-muted">{hint}</p>}
      {error && (
        <p className="text-xs text-danger-fg" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & FieldWrapperProps;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, className, id, ...rest },
  ref
) {
  // Callers rarely pass an id (react-hook-form spreads name/onChange only),
  // so generate one: without it the <label> is not programmatically bound to
  // its control and screen readers announce an unlabelled field.
  const generatedId = useId();
  const fieldId = id ?? generatedId;

  return (
    <FieldWrapper label={label} error={error} hint={hint} htmlFor={fieldId}>
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        className={clsx(fieldBase, error && "border-danger-700", className)}
        {...rest}
      />
    </FieldWrapper>
  );
});

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & FieldWrapperProps;

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, hint, className, id, ...rest },
  ref
) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;

  return (
    <FieldWrapper label={label} error={error} hint={hint} htmlFor={fieldId}>
      <textarea
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        className={clsx(fieldBase, "min-h-28 resize-y", error && "border-danger-700", className)}
        {...rest}
      />
    </FieldWrapper>
  );
});

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & FieldWrapperProps;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, hint, className, id, children, ...rest },
  ref
) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;

  return (
    <FieldWrapper label={label} error={error} hint={hint} htmlFor={fieldId}>
      <select
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        className={clsx(fieldBase, error && "border-danger-700", className)}
        {...rest}
      >
        {children}
      </select>
    </FieldWrapper>
  );
});
