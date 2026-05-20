import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { resolveRegistryFetchUrl } from '@/lib/registry';

describe('resolveRegistryFetchUrl', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv, NODE_ENV: 'development' };
    delete process.env.REGISTRY_URL;
    delete process.env.PORT;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('uses GitHub default when REGISTRY_URL is unset', () => {
    expect(resolveRegistryFetchUrl()).toContain('raw.githubusercontent.com');
  });

  it('rewrites localhost registry.json to process.env.PORT in development', () => {
    process.env.REGISTRY_URL = 'http://127.0.0.1:3000/registry.json';
    process.env.PORT = '3010';
    expect(resolveRegistryFetchUrl()).toBe('http://127.0.0.1:3010/registry.json');
  });

  it('does not rewrite remote REGISTRY_URL', () => {
    process.env.REGISTRY_URL = 'https://example.com/registry.json';
    process.env.PORT = '3010';
    expect(resolveRegistryFetchUrl()).toBe('https://example.com/registry.json');
  });

  it('does not rewrite in production', () => {
    process.env.NODE_ENV = 'production';
    process.env.REGISTRY_URL = 'http://127.0.0.1:3000/registry.json';
    process.env.PORT = '3010';
    expect(resolveRegistryFetchUrl()).toBe('http://127.0.0.1:3000/registry.json');
  });
});
