#!/usr/bin/env node
/**
 * Pre-M2 validation: Test registry.json fetch.
 * Run: node apps/web/scripts/validate-registry-fetch.mjs
 * Optional: REGISTRY_URL=https://... node ...
 */
const url =
  process.env.REGISTRY_URL ||
  'https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json';

console.log('Fetching:', url);

fetch(url)
  .then((r) => {
    console.log('Status:', r.status, r.statusText);
    if (!r.ok) {
      throw new Error(`HTTP ${r.status}`);
    }
    return r.json();
  })
  .then((d) => {
    if (!Array.isArray(d)) {
      console.error('❌ Response is not an array');
      process.exit(1);
    }
    console.log('✓ Agents count:', d.length);
    console.log('✅ Registry fetch OK');
  })
  .catch((e) => {
    console.error('❌ Error:', e.message);
    process.exit(1);
  });
