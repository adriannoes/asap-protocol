"use client";

import { useChat } from "@ai-sdk/react";
import {
  type AgentContext,
  type HostContext,
  LocalStorage,
  connectAgent,
  createAgent,
  createHost,
  resumeAgent,
  resumeHost,
} from "@asap-protocol/client";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useEffect, useRef, useState } from "react";

const SESSION_META_KEY = "asap-example/session-meta";

function parseCapabilitiesFromEnv(): string[] {
  const raw = process.env.NEXT_PUBLIC_ASAP_CAPABILITIES;
  if (raw === undefined || raw.trim() === "") {
    return ["urn:asap:cap:echo"];
  }
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function defaultProviderUrl(): string {
  return process.env.NEXT_PUBLIC_ASAP_PROVIDER_URL ?? "http://127.0.0.1:8000";
}

function resolveAudience(providerUrl: string): string {
  const fromEnv = process.env.NEXT_PUBLIC_ASAP_AUDIENCE;
  if (fromEnv !== undefined && fromEnv.trim() !== "") {
    return fromEnv.trim();
  }
  try {
    return new URL(providerUrl).origin;
  } catch {
    return providerUrl;
  }
}

function textFromUiMessage(message: UIMessage): string {
  return message.parts
    .filter((part): part is { type: "text"; text: string } => part.type === "text")
    .map((part) => part.text)
    .join("");
}

/** Snapshot at module load (NEXT_PUBLIC_* inlined by Next). */
const DEMO_CAPABILITIES = parseCapabilitiesFromEnv();

export function AsapDemo() {
  const [identityReady, setIdentityReady] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [providerUrl, setProviderUrl] = useState(defaultProviderUrl);
  const [connected, setConnected] = useState(false);
  const [connBusy, setConnBusy] = useState(false);
  const [connError, setConnError] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const hostRef = useRef<HostContext | null>(null);
  const agentRef = useRef<AgentContext | null>(null);
  const providerUrlRef = useRef(providerUrl);
  const audienceRef = useRef(resolveAudience(providerUrl));
  const capsRef = useRef(DEMO_CAPABILITIES);

  useEffect(() => {
    providerUrlRef.current = providerUrl;
    audienceRef.current = resolveAudience(providerUrl);
  }, [providerUrl]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const storage = new LocalStorage("asap-example/sdk/");
        const metaRaw =
          typeof window !== "undefined" ? window.localStorage.getItem(SESSION_META_KEY) : null;
        const parsedMeta =
          metaRaw !== null && metaRaw.length > 0
            ? (JSON.parse(metaRaw) as { hostId?: unknown; agentId?: unknown })
            : null;

        let host: HostContext;
        let agent: AgentContext;

        if (
          parsedMeta !== null &&
          typeof parsedMeta.hostId === "string" &&
          typeof parsedMeta.agentId === "string"
        ) {
          host = await resumeHost({ storage, hostId: parsedMeta.hostId });
          agent = await resumeAgent(host, { agentId: parsedMeta.agentId, mode: "delegated" });
        } else {
          host = await createHost({ storage });
          agent = await createAgent(host, { mode: "delegated" });
          window.localStorage.setItem(
            SESSION_META_KEY,
            JSON.stringify({ hostId: host.hostId, agentId: agent.agentId }),
          );
        }

        if (!cancelled) {
          hostRef.current = host;
          agentRef.current = agent;
          setIdentityReady(true);
        }
      } catch (err) {
        if (!cancelled) {
          setInitError(err instanceof Error ? err.message : String(err));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const [transport] = useState(
    () =>
      new DefaultChatTransport({
        api: "/api/chat",
        prepareSendMessagesRequest: async ({ body, messages }) => {
          const agent = agentRef.current;
          if (agent === null) {
            throw new Error("Agent not initialized");
          }
          const audience = audienceRef.current;
          const jwt = await agent.signAgentJwt({
            aud: audience,
            capabilities: capsRef.current,
          });
          return {
            body: {
              ...(body ?? {}),
              messages,
              providerUrl: providerUrlRef.current,
              audience,
              capabilities: capsRef.current,
              agentJwt: jwt,
            },
          };
        },
      }),
  );

  const { messages, sendMessage, status, error } = useChat({
    transport,
  });

  async function onConnect(): Promise<void> {
    const host = hostRef.current;
    const agent = agentRef.current;
    if (host === null || agent === null) {
      return;
    }
    setConnBusy(true);
    setConnError(null);
    try {
      const provider = new URL(providerUrl);
      const audience = resolveAudience(providerUrl);
      audienceRef.current = audience;
      await connectAgent(provider, host, agent, capsRef.current, "delegated", {
        audience,
      });
      setConnected(true);
    } catch (err) {
      setConnError(err instanceof Error ? err.message : String(err));
    } finally {
      setConnBusy(false);
    }
  }

  async function onSend(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    const text = input.trim();
    if (text === "" || !connected) {
      return;
    }
    setInput("");
    await sendMessage({ text });
  }

  const chatDisabled = !identityReady || !connected || status === "streaming" || status === "submitted";

  return (
    <>
      <section className="panel">
        <label htmlFor="provider-url">Gateway base URL</label>
        <input
          id="provider-url"
          type="url"
          value={providerUrl}
          onChange={(e) => setProviderUrl(e.target.value)}
          disabled={connected || connBusy}
          placeholder="https://your-asap-gateway.example"
          autoComplete="url"
        />
        <div className="row">
          <button type="button" className="primary" disabled={!identityReady || connected || connBusy} onClick={() => void onConnect()}>
            {connBusy ? "Connecting…" : "Connect agent"}
          </button>
          {connected ? <span className="status-line ok">Agent registered with provider.</span> : null}
        </div>
        {initError !== null ? <p className="status-line err">Identity error: {initError}</p> : null}
        {connError !== null ? <p className="status-line err">{connError}</p> : null}
        {!identityReady && initError === null ? <p className="status-line">Initializing host / agent in localStorage…</p> : null}
      </section>

      <section className="panel">
        <p className="status-line">
          Capabilities (from <code>NEXT_PUBLIC_ASAP_CAPABILITIES</code>): {DEMO_CAPABILITIES.join(", ") || "(none)"}
        </p>
        <p className="status-line">
          Set <code>OPENAI_API_KEY</code> locally for chat. HTTPS recommended for real gateways and tokens.
        </p>

        <div className="messages" aria-live="polite">
          {messages.map((m) => (
            <div key={m.id} className={`msg ${m.role}`}>
              {textFromUiMessage(m)}
            </div>
          ))}
        </div>

        <form className="composer" onSubmit={(e) => void onSend(e)}>
          <textarea
            className="composer-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={connected ? "Message the model (it can call ASAP tools)…" : "Connect to the gateway first…"}
            disabled={chatDisabled}
            rows={2}
          />
          <button type="submit" className="primary" disabled={chatDisabled}>
            Send
          </button>
        </form>
        {error !== undefined ? <p className="status-line err">{error.message}</p> : null}
        {status === "streaming" ? <p className="status-line">Streaming…</p> : null}
      </section>
    </>
  );
}
