import { describe, expect, it } from 'vitest';

import { formatRegistryEnumLabel } from '@/lib/hardware-labels';

describe('formatRegistryEnumLabel', () => {
    it('title-cases snake_case registry enum values', () => {
        expect(formatRegistryEnumLabel('edge_accelerator')).toBe('Edge Accelerator');
        expect(formatRegistryEnumLabel('local_cuda')).toBe('Local Cuda');
    });

    it('returns empty string unchanged', () => {
        expect(formatRegistryEnumLabel('')).toBe('');
    });

    it('preserves empty segments from repeated underscores', () => {
        expect(formatRegistryEnumLabel('a__b')).toBe('A  B');
    });
});
