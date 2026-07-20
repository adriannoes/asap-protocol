import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { resolveRegistryFetchUrl } from '@/lib/registry';

describe('resolveRegistryFetchUrl', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    vi.stubEnv('NODE_ENV', 'development');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('uses GitHub default when REGISTRY_URL is unset', () => {
    expect(resolveRegistryFetchUrl()).toBe(
      'https://raw.githubusercontent.com/asap-protocol/asap-protocol/main/registry.json'
    );
  });

  it('rewrites localhost registry.json to process.env.PORT in development', () => {
    vi.stubEnv('REGISTRY_URL', 'http://127.0.0.1:3000/registry.json');
    vi.stubEnv('PORT', '3010');
    expect(resolveRegistryFetchUrl()).toBe('http://127.0.0.1:3010/registry.json');
  });

  it('does not rewrite remote REGISTRY_URL', () => {
    vi.stubEnv('REGISTRY_URL', 'https://example.com/registry.json');
    vi.stubEnv('PORT', '3010');
    expect(resolveRegistryFetchUrl()).toBe('https://example.com/registry.json');
  });

  it('does not rewrite in production', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('REGISTRY_URL', 'http://127.0.0.1:3000/registry.json');
    vi.stubEnv('PORT', '3010');
    expect(resolveRegistryFetchUrl()).toBe('http://127.0.0.1:3000/registry.json');
  });
});
