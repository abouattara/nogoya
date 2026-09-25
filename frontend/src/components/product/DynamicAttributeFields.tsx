"use client";

import { Input, Select } from "@/components/ui/Input";
import type { AttributeValue, CategoryAttribute } from "@/lib/types";

export type AttributeValues = Record<string, AttributeValue>;

/**
 * Renders the form fields declared by the selected category
 * (CategoryAttribute rows) — no field is hard-coded in the frontend.
 */
export function DynamicAttributeFields({
  attributes,
  values,
  errors,
  onChange,
}: {
  attributes: CategoryAttribute[];
  values: AttributeValues;
  errors?: Record<string, string>;
  onChange: (slug: string, value: AttributeValue) => void;
}) {
  if (attributes.length === 0) return null;

  return (
    <fieldset className="flex flex-col gap-3 rounded-xl border border-border p-4">
      <legend className="px-1 text-sm font-semibold">Caractéristiques</legend>
      <p className="text-xs text-foreground-muted">
        Ces champs dépendent de la catégorie choisie et aident les visiteurs à filtrer.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {attributes.map((attribute) => {
          const value = values[attribute.slug];
          const label = attribute.unit ? `${attribute.name} (${attribute.unit})` : attribute.name;
          const error = errors?.[attribute.slug];
          const fieldId = `attr-${attribute.slug}`;

          if (attribute.attribute_type === "boolean") {
            return (
              <div key={attribute.slug} className="flex flex-col gap-1">
                <label htmlFor={fieldId} className="flex items-center gap-2 text-sm font-medium">
                  <input
                    id={fieldId}
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(e) => onChange(attribute.slug, e.target.checked)}
                  />
                  {label}
                  {attribute.required && <span aria-hidden="true"> *</span>}
                </label>
                {error && (
                  <p className="text-xs text-danger-fg" role="alert">
                    {error}
                  </p>
                )}
              </div>
            );
          }

          if (attribute.attribute_type === "select") {
            return (
              <Select
                key={attribute.slug}
                id={fieldId}
                label={attribute.required ? `${label} *` : label}
                value={typeof value === "string" ? value : ""}
                error={error}
                onChange={(e) => onChange(attribute.slug, e.target.value)}
              >
                <option value="">— Choisir —</option>
                {attribute.options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            );
          }

          if (attribute.attribute_type === "multi_select") {
            const selected = Array.isArray(value) ? value : [];
            return (
              <div key={attribute.slug} className="flex flex-col gap-1">
                <span className="text-sm font-medium">{attribute.required ? `${label} *` : label}</span>
                <div className="flex flex-wrap gap-2">
                  {attribute.options.map((option) => {
                    const checked = selected.includes(option);
                    return (
                      <label
                        key={option}
                        className={`cursor-pointer rounded-lg border px-2 py-1 text-sm ${
                          checked
                            ? "border-brand-300 bg-brand-50 text-brand-800"
                            : "border-border bg-surface text-foreground"
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={checked}
                          onChange={() =>
                            onChange(
                              attribute.slug,
                              checked ? selected.filter((v) => v !== option) : [...selected, option]
                            )
                          }
                        />
                        {option}
                      </label>
                    );
                  })}
                </div>
                {error && (
                  <p className="text-xs text-danger-fg" role="alert">
                    {error}
                  </p>
                )}
              </div>
            );
          }

          return (
            <Input
              key={attribute.slug}
              id={fieldId}
              label={attribute.required ? `${label} *` : label}
              type={
                attribute.attribute_type === "number"
                  ? "number"
                  : attribute.attribute_type === "date"
                    ? "date"
                    : "text"
              }
              value={value === undefined || value === null ? "" : String(value)}
              error={error}
              onChange={(e) =>
                onChange(
                  attribute.slug,
                  attribute.attribute_type === "number"
                    ? e.target.value === ""
                      ? ""
                      : Number(e.target.value)
                    : e.target.value
                )
              }
            />
          );
        })}
      </div>
    </fieldset>
  );
}
