import { z, type ZodType } from "zod";

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
    case "array":
      return z.array(z.unknown());
    default:
      return z.record(z.string(), z.unknown());
  }
}
