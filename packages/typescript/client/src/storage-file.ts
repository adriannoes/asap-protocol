/**
 * Node.js filesystem-backed {@link Storage} (optional server-side).
 */

import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

import type { Storage } from "./storage-local.js";

function keyToSafeRelativePath(key: string): string {
  const segments = key.split("/").filter((s) => s.length > 0 && s !== "." && s !== "..");
  if (segments.length === 0) {
    return "_empty.key";
  }
  return path.join(...segments);
}

function isNodeError(e: unknown): e is NodeJS.ErrnoException {
  return typeof e === "object" && e !== null && "code" in e;
}

/**
 * Filesystem-backed storage under a dedicated directory (Node.js only).
 *
 * Keys with `/` map to nested paths; `..` segments are stripped.
 */
export class FileStorage implements Storage {
  constructor(private readonly baseDir: string) {}

  private absolutePath(key: string): string {
    return path.resolve(this.baseDir, keyToSafeRelativePath(key));
  }

  async get(key: string): Promise<string | undefined> {
    const target = this.absolutePath(key);
    try {
      return await readFile(target, "utf8");
    } catch (e) {
      if (isNodeError(e) && e.code === "ENOENT") {
        return undefined;
      }
      throw e;
    }
  }

  async set(key: string, value: string): Promise<void> {
    const target = this.absolutePath(key);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, value, "utf8");
  }

  async delete(key: string): Promise<void> {
    const target = this.absolutePath(key);
    try {
      await unlink(target);
    } catch (e) {
      if (isNodeError(e) && e.code === "ENOENT") {
        return;
      }
      throw e;
    }
  }
}
