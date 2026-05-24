/**
 * Human-readable labels for registry hardware / inference enum values.
 */

/** Format snake_case registry enum values for UI display. */
export function formatRegistryEnumLabel(value: string): string {
    return value
        .split('_')
        .map((part) => (part.length > 0 ? part[0].toUpperCase() + part.slice(1) : part))
        .join(' ');
}
