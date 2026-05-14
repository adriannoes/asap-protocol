import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { afterEach, describe, expect, it } from "vitest";

import { FileStorage } from "../src/storage-file.js";

describe("FileStorage edge paths", () => {
  let dir: string;

  afterEach(async () => {
    if (dir) await rm(dir, { recursive: true, force: true });
  });

  it("maps empty key segments to _empty.key", async () => {
    dir = await mkdtemp(path.join(tmpdir(), "asap-fs-"));
    const fs = new FileStorage(dir);
    await fs.set("//", "empty-key");
    expect(await fs.get("//")).toBe("empty-key");
  });
});
