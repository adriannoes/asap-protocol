/**
 * Node / desktop-only storage backends (`fs`, optional `keytar`).
 * Import from `@asap-protocol/client/storage-node` so browser bundles do not pull Node built-ins.
 */

export { FileStorage } from "./storage-file.js";
export { KeychainStorage, type KeychainLike } from "./storage-keychain.js";
