import { z, type ZodType } from "zod";

type EnumLiteralKind = "string" | "number" | "boolean" | "null" | "unsupported";

function enumLiteralKind(value: unknown): EnumLiteralKind {
  if (value === null) {
    return "null";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return typeof value as "string" | "number" | "boolean";
  }
  return "unsupported";
}

function zodFromJsonSchemaEnum(enumValues: unknown[]): ZodType<unknown> {
  if (enumValues.length === 0) {
    throw new Error("JSON Schema enum must contain at least one value");
  }

  const kinds = new Set<EnumLiteralKind>();
  for (const value of enumValues) {
    kinds.add(enumLiteralKind(value));
  }

  if (kinds.has("unsupported")) {
    throw new Error("JSON Schema enum supports only string, number, boolean, and null literals");
  }

  const nonNullKinds = [...kinds].filter((kind) => kind !== "null");
  if (nonNullKinds.length > 1) {
    throw new Error(
      `JSON Schema enum with mixed primitive types is unsupported (found: ${[...kinds].join(", ")})`,
    );
  }

  const literals = enumValues.map((value) => {
    if (value === null) {
      return z.null();
    }
    if (typeof value === "string") {
      return z.literal(value);
    }
    if (typeof value === "number") {
      return z.literal(value);
    }
    return z.literal(value as boolean);
  });

  return literals.length === 1
    ? literals[0]!
    : z.union(literals as unknown as [ZodType<unknown>, ZodType<unknown>, ...ZodType<unknown>[]]);
}

/**
 * Minimal JSON Schema → Zod bridge for adapter tool schemas (subset only).
 *
 * Lossy for `$ref` / complex `oneOf`; mirrors `@asap-protocol/mastra` / legacy Chat Completions adapter patterns.
 */
export function zodFromJsonSchema(schema: Record<string, unknown>): ZodType<unknown> {
  if ("$ref" in schema) {
    return z.record(z.string(), z.unknown());
  }
  if ("oneOf" in schema && Array.isArray(schema.oneOf)) {
    const branches = schema.oneOf
      .filter((s): s is Record<string, unknown> => typeof s === "object" && s !== null && !Array.isArray(s))
      .map((s) => zodFromJsonSchema(s));
    return branches.length === 0
      ? z.unknown()
      : branches.length === 1
        ? branches[0]!
        : z.union(branches as [ZodType<unknown>, ZodType<unknown>, ...ZodType<unknown>[]]);
  }
  if ("enum" in schema && Array.isArray(schema.enum) && schema.enum.length > 0) {
    return zodFromJsonSchemaEnum(schema.enum);
  }
  switch (schema.type) {
    case "object": {
      const maybeProps = schema.properties;
      if (
        maybeProps !== undefined &&
        typeof maybeProps === "object" &&
        maybeProps !== null &&
        !Array.isArray(maybeProps)
      ) {
        const propsRecord = maybeProps as Record<string, unknown>;
        const required = new Set(
          Array.isArray(schema.required) ? schema.required.filter((k): k is string => typeof k === "string") : [],
        );
        const shape: Record<string, ZodType<unknown>> = {};
        for (const [key, val] of Object.entries(propsRecord)) {
          if (typeof val === "object" && val !== null && !Array.isArray(val)) {
            const child = zodFromJsonSchema(val as Record<string, unknown>);
            shape[key] = required.has(key) ? child : child.optional();
          }
        }
        if (Object.keys(shape).length > 0) {
          return z.object(shape);
        }
      }
      return z.record(z.string(), z.unknown());
    }
    case "string":
      return z.string();
    case "number":
    case "integer":
      return z.number();
    case "boolean":
      return z.boolean();
    case "array": {
      const items = schema.items;
      if (typeof items === "object" && items !== null && !Array.isArray(items)) {
        return z.array(zodFromJsonSchema(items as Record<string, unknown>));
      }
      return z.array(z.unknown());
    }
    default:
      return z.record(z.string(), z.unknown());
  }
}
