# ASAP CA Test Fixtures

Test CA keypair for Verified badge simulation (Task 2.2).

- `ca_private.pem`: Ed25519 private key (PEM)
- `ca_public_b64.txt`: Base64-encoded public key for `verify_ca_signature(known_cas=...)`

**Security**: These keys are for testing only. Do not use in production.

**Regenerating signed fixtures**: When the Manifest model changes (e.g. new fields),
run `uv run python scripts/regenerate_signed_fixtures.py` to update
`verified_manifest.json` and `self_signed_manifest.json` so signatures match
the current canonical form.
