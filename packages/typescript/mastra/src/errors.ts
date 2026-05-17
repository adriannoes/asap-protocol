export {
  FatalError,
  RecoverableError,
  RemoteFatalRPCError,
  RemoteRecoverableRPCError,
} from "@asap-protocol/client";

/**
 * Raised when the provider indicates an approval step is required before the capability can run.
 */
export class ApprovalRequiredError extends Error {
  override readonly name = "ApprovalRequiredError";

  readonly detail: unknown;

  constructor(message = "Capability execution requires approval", detail?: unknown) {
    super(message);
    this.detail = detail;
  }
}

/**
 * Raised when the agent JWT is valid but the capability is not granted (HTTP 403 `capability_not_granted`).
 * Call {@link CapabilityNotGrantedError.requestCapability} to run the optional `requestCapability` hook supplied to `asapToolsForMastra` options.
 */
export class CapabilityNotGrantedError extends Error {
  override readonly name = "CapabilityNotGrantedError";

  readonly requiredCapability: string;

  private readonly hook?: (capability: string) => void | Promise<void>;

  constructor(
    requiredCapability: string,
    requestCapability?: (capability: string) => void | Promise<void>,
    message?: string,
  ) {
    super(message ?? `Capability not granted: ${requiredCapability}`);
    this.requiredCapability = requiredCapability;
    this.hook = requestCapability;
  }

  requestCapability(): void | Promise<void> {
    return this.hook?.(this.requiredCapability);
  }
}
