#!/usr/bin/env node
/**
 * Runs `asap compliance-check` against `ASAP_PROVIDER_URL` (repo root, `--exit-on-fail`).
 *
 * Expects `uv` on PATH and ASAP checked out locally (Compliance Harness bundled with asap-protocol).
 * Configure `ASAP_PROVIDER_URL` in `.env` or the environment — see `.env.example`.
 */

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "../../..");

const url = process.env.ASAP_PROVIDER_URL?.trim();

if (!url) {
  console.error("Missing ASAP_PROVIDER_URL — set it to your gateway base URL (e.g. https://petstore-gateway.example)");
  process.exit(1);
}

try {
  void new URL(url);
} catch {
  console.error(`Invalid ASAP_PROVIDER_URL — not a valid absolute URL: ${url}`);
  process.exit(1);
}

const result = spawnSync("uv", ["run", "asap", "compliance-check", "--url", url, "--exit-on-fail"], {
  cwd: repoRoot,
  stdio: "inherit",
});

process.exit(typeof result.status === "number" ? result.status : 1);
