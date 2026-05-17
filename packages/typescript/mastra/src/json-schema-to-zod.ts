import { z, type ZodType } from "zod";

/**
 * Minimal JSON Schema → Zod bridge for adapter tool schemas (subset only; see tests for `oneOf` / `$ref`).
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
  switch (schema.type) {
    case "object":
      return z.record(z.string(), z.unknown());
    case "string":
      return z.string();
    case "number":
    case "integer":
      return z.number();
    case "boolean":
      return z.boolean();
    case "array":
      return z.array(z.unknown());
    default:
      return z.record(z.string(), z.unknown());
  }
}
