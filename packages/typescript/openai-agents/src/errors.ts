export {
  FatalError,
  RecoverableError,
  RemoteFatalRPCError,
  RemoteRecoverableRPCError,
} from "@asap-protocol/client";

/**
 * Structured `approval_required` payload (`error.data`) from an ASAP provider JSON body.
 */
export interface ApprovalRequiredDetail {
  readonly reason?: string;
  readonly approval_url?: string;
}

function approvalDetailFromUnknown(data: unknown): ApprovalRequiredDetail | undefined {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return undefined;
  }
  const rec = data as Record<string, unknown>;
  const reason = rec.reason;
  const approval_url = rec.approval_url;
  const detail: { reason?: string; approval_url?: string } = {};
  if (typeof reason === "string") {
    detail.reason = reason;
  }
  if (typeof approval_url === "string") {
    detail.approval_url = approval_url;
  }
  return Object.keys(detail).length > 0 ? (detail as ApprovalRequiredDetail) : undefined;
}

/**
 * Raised when the provider indicates an approval step is required before the capability can run.
 */
export class ApprovalRequiredError extends Error {
  override readonly name = "ApprovalRequiredError";

  readonly detail?: ApprovalRequiredDetail;

  constructor(message = "Capability execution requires approval", detail?: unknown) {
    super(message);
    this.detail = approvalDetailFromUnknown(detail);
  }
}

/**
 * Raised when the agent JWT is valid but the capability is not granted (HTTP 403 `capability_not_granted`).
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
