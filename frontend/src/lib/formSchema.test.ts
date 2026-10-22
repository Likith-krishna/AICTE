import { describe, it, expect } from 'vitest';
import { buildZodSchema, toPayload, defaultValues, groupBySection } from './formSchema';
import type { FormField, FormSchema } from '@/types/api';

const textField: FormField = {
  name: 'contact_person_name', label: 'Contact person name', type: 'text',
  required: true, max_length: 200, section: 'Contact',
};

const emailField: FormField = {
  name: 'contact_email', label: 'Contact email', type: 'email', required: true, section: 'Contact',
};

const intField: FormField = {
  name: 'current_intake', label: 'Current approved intake', type: 'integer', required: true, min: 0, max: 10000,
};

const greaterField: FormField = {
  name: 'proposed_intake', label: 'Proposed intake', type: 'integer', required: true, min: 1, max: 10000,
  greater_than_field: 'current_intake',
};

const nameField: FormField = { name: 'current_name', label: 'Current name', type: 'text', required: true };
const differentField: FormField = {
  name: 'proposed_name', label: 'Proposed name', type: 'text', required: true, different_from_field: 'current_name',
};

const checkboxField: FormField = {
  name: 'declaration', label: 'I confirm the information is accurate.', type: 'checkbox', required: true,
};

const selectField: FormField = {
  name: 'level', label: 'Level', type: 'select', required: true, options: ['Diploma', 'Under Graduate'],
};

function schemaOf(fields: FormField[]): FormSchema {
  return {
    category_code: 'TEST', version: 1, verification_status: 'VERIFIED',
    verification_note: '', has_category_fields: true, fields,
  };
}

describe('buildZodSchema', () => {
  it('rejects a missing required text field and accepts a filled one', () => {
    const schema = buildZodSchema(schemaOf([textField]), { partial: false });
    expect(schema.safeParse({ contact_person_name: '' }).success).toBe(false);
    expect(schema.safeParse({ contact_person_name: 'Jane Doe' }).success).toBe(true);
  });

  it('in partial (draft) mode, a required field becomes optional', () => {
    const schema = buildZodSchema(schemaOf([textField]), { partial: true });
    expect(schema.safeParse({ contact_person_name: '' }).success).toBe(true);
  });

  it('validates email format', () => {
    const schema = buildZodSchema(schemaOf([emailField]), { partial: false });
    expect(schema.safeParse({ contact_email: 'not-an-email' }).success).toBe(false);
    expect(schema.safeParse({ contact_email: 'a@b.com' }).success).toBe(true);
  });

  it('enforces integer min/max bounds', () => {
    const schema = buildZodSchema(schemaOf([intField]), { partial: false });
    expect(schema.safeParse({ current_intake: -1 }).success).toBe(false);
    expect(schema.safeParse({ current_intake: 10001 }).success).toBe(false);
    expect(schema.safeParse({ current_intake: 60 }).success).toBe(true);
  });

  it('enforces greater_than_field across two fields', () => {
    const schema = buildZodSchema(schemaOf([intField, greaterField]), { partial: false });
    const tooLow = schema.safeParse({ current_intake: 60, proposed_intake: 60 });
    expect(tooLow.success).toBe(false);
    const ok = schema.safeParse({ current_intake: 60, proposed_intake: 120 });
    expect(ok.success).toBe(true);
  });

  it('enforces different_from_field (case/whitespace-insensitive)', () => {
    const schema = buildZodSchema(schemaOf([nameField, differentField]), { partial: false });
    const same = schema.safeParse({ current_name: 'ABC Trust', proposed_name: ' abc trust ' });
    expect(same.success).toBe(false);
    const different = schema.safeParse({ current_name: 'ABC Trust', proposed_name: 'XYZ Trust' });
    expect(different.success).toBe(true);
  });

  it('requires a checkbox to be literally true, not just truthy', () => {
    const schema = buildZodSchema(schemaOf([checkboxField]), { partial: false });
    expect(schema.safeParse({ declaration: false }).success).toBe(false);
    expect(schema.safeParse({ declaration: true }).success).toBe(true);
  });

  it('restricts a select field to its listed options', () => {
    const schema = buildZodSchema(schemaOf([selectField]), { partial: false });
    expect(schema.safeParse({ level: 'Not A Real Level' }).success).toBe(false);
    expect(schema.safeParse({ level: 'Under Graduate' }).success).toBe(true);
  });
});

describe('toPayload', () => {
  it('omits blank strings and trims non-blank ones', () => {
    const schema = schemaOf([textField, emailField]);
    const payload = toPayload(schema, { contact_person_name: '  Jane  ', contact_email: '' });
    expect(payload).toEqual({ contact_person_name: 'Jane' });
  });

  it('keeps numeric integer values and drops NaN', () => {
    const schema = schemaOf([intField]);
    expect(toPayload(schema, { current_intake: 60 })).toEqual({ current_intake: 60 });
    expect(toPayload(schema, { current_intake: NaN })).toEqual({});
  });

  it('always includes a boolean checkbox value', () => {
    const schema = schemaOf([checkboxField]);
    expect(toPayload(schema, { declaration: false })).toEqual({ declaration: false });
    expect(toPayload(schema, { declaration: true })).toEqual({ declaration: true });
  });
});

describe('defaultValues', () => {
  it('fills in type-appropriate empty defaults for missing data', () => {
    const schema = schemaOf([textField, intField, checkboxField]);
    expect(defaultValues(schema, {})).toEqual({
      contact_person_name: '', current_intake: undefined, declaration: false,
    });
  });

  it('preserves existing values of the right type', () => {
    const schema = schemaOf([textField, intField]);
    expect(defaultValues(schema, { contact_person_name: 'Jane', current_intake: 60 }))
      .toEqual({ contact_person_name: 'Jane', current_intake: 60 });
  });
});

describe('groupBySection', () => {
  it('groups fields by section, defaulting to "Details"', () => {
    const grouped = groupBySection([textField, emailField, { ...intField, section: undefined }]);
    const map = Object.fromEntries(grouped);
    expect(map['Contact'].map((f) => f.name)).toEqual(['contact_person_name', 'contact_email']);
    expect(map['Details'].map((f) => f.name)).toEqual(['current_intake']);
  });
});
