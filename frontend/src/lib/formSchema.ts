import { z } from 'zod';
import type { FormField, FormSchema } from '@/types/api';

/**
 * Builds the Zod validator from the backend-served form schema, so the browser
 * and the API validate against one definition. The backend re-validates
 * everything; this exists for immediate, field-level feedback.
 */

const emptyToUndefined = (v: unknown) => (v === '' || v === null || (typeof v === 'number' && Number.isNaN(v)) ? undefined : v);

function fieldValidator(f: FormField, partial: boolean): z.ZodTypeAny {
  const required = !!f.required && !partial;
  switch (f.type) {
    case 'integer': {
      let n = z.number({ invalid_type_error: 'Must be a whole number', required_error: 'This field is required' })
        .int('Must be a whole number');
      if (f.min !== undefined) n = n.min(f.min, `Must be at least ${f.min}`);
      if (f.max !== undefined) n = n.max(f.max, `Must be at most ${f.max}`);
      return z.preprocess(emptyToUndefined, required ? n : n.optional());
    }
    case 'checkbox':
      return required
        ? z.literal(true, { errorMap: () => ({ message: 'You must accept the declaration' }) })
        : z.boolean().optional();
    default: {
      let s = z.string({ required_error: 'This field is required' }).trim();
      if (required) s = s.min(1, 'This field is required');
      if (f.min_length && !partial) s = s.min(f.min_length, `Must be at least ${f.min_length} characters`);
      if (f.max_length) s = s.max(f.max_length, `Must be at most ${f.max_length} characters`);
      let out: z.ZodTypeAny = s;
      if (f.type === 'email') out = s.refine((v) => v === '' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v), 'Enter a valid email address');
      if (f.pattern) {
        const re = new RegExp(f.pattern);
        out = out.refine((v: string) => v === '' || re.test(v), 'Invalid format');
      }
      if (f.type === 'select' && f.options) {
        const opts = f.options;
        out = out.refine((v: string) => v === '' || opts.includes(v), 'Choose one of the listed options');
      }
      return required ? out : z.preprocess(emptyToUndefined, out.optional());
    }
  }
}

export function buildZodSchema(schema: FormSchema, { partial }: { partial: boolean }) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const f of schema.fields) shape[f.name] = fieldValidator(f, partial);
  const labels = Object.fromEntries(schema.fields.map((f) => [f.name, f.label.toLowerCase()]));

  return z.object(shape).superRefine((data, ctx) => {
    if (partial) return;
    for (const f of schema.fields) {
      const v = data[f.name];
      if (f.greater_than_field) {
        const other = data[f.greater_than_field];
        if (typeof v === 'number' && typeof other === 'number' && v <= other) {
          ctx.addIssue({ code: z.ZodIssueCode.custom, path: [f.name], message: `Must be greater than ${labels[f.greater_than_field]}` });
        }
      }
      if (f.different_from_field) {
        const other = data[f.different_from_field];
        if (typeof v === 'string' && typeof other === 'string' && v.trim().toLowerCase() === other.trim().toLowerCase()) {
          ctx.addIssue({ code: z.ZodIssueCode.custom, path: [f.name], message: `Must differ from ${labels[f.different_from_field]}` });
        }
      }
    }
  });
}

/** Normalises RHF values into the API payload (blank → omitted, numbers kept numeric). */
export function toPayload(schema: FormSchema, values: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of schema.fields) {
    const v = values[f.name];
    if (f.type === 'checkbox') {
      if (typeof v === 'boolean') out[f.name] = v;
      continue;
    }
    if (f.type === 'integer') {
      if (typeof v === 'number' && !Number.isNaN(v)) out[f.name] = v;
      continue;
    }
    if (typeof v === 'string' && v.trim() !== '') out[f.name] = v.trim();
  }
  return out;
}

export function defaultValues(schema: FormSchema, data: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of schema.fields) {
    const v = data[f.name];
    if (f.type === 'checkbox') out[f.name] = v === true;
    else if (f.type === 'integer') out[f.name] = typeof v === 'number' ? v : undefined;
    else out[f.name] = typeof v === 'string' ? v : '';
  }
  return out;
}

export function groupBySection(fields: FormField[]): [string, FormField[]][] {
  const groups = new Map<string, FormField[]>();
  for (const f of fields) {
    const key = f.section ?? 'Details';
    groups.set(key, [...(groups.get(key) ?? []), f]);
  }
  return [...groups.entries()];
}
