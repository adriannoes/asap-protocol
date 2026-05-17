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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useEffect, useRef, useState } from "react";

const SESSION_META_KEY = "asap-mastra-example/session-meta";

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
  return process.env.NEXT_PUBLIC_ASAP_PROVIDER_URL ?? "http://127.0.0.1:8080";
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

function isLocalHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

const DEMO_CAPABILITIES = parseCapabilitiesFromEnv();

export function MastraChatDemo() {
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
        const storage = new LocalStorage("asap-mastra-example/sdk/");
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
      hostRef.current = null;
      agentRef.current = null;
    };
  }, []);

  /* eslint-disable react-hooks/refs -- `useState` lazy init closes over refs; they are read only inside async `prepareSendMessagesRequest`, not during render. */
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
          const currentProvider = providerUrlRef.current;
          if (process.env.NODE_ENV !== "production") {
            try {
              const u = new URL(currentProvider);
              if (u.protocol === "http:" && !isLocalHostname(u.hostname) && jwt.length > 0) {
                console.warn(
                  "[example-mastra] Signing ASAP agent JWT over non-localhost HTTP is replay-prone; prefer HTTPS for real gateways.",
                );
              }
            } catch {
              // ignore invalid URL here; connect flow validates separately
            }
          }
          return {
            body: {
              ...(body ?? {}),
              messages,
              providerUrl: currentProvider,
              capabilities: capsRef.current,
              agentJwt: jwt,
            },
          };
        },
      }),
  );
  /* eslint-enable react-hooks/refs */

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
    <div className="mt-8 flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Gateway connection</CardTitle>
          <CardDescription>Point the demo at your ASAP HTTP gateway before chatting.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="provider-url" className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
              Gateway base URL
            </label>
            <Input
              id="provider-url"
              type="url"
              value={providerUrl}
              onChange={(e) => setProviderUrl(e.target.value)}
              disabled={connected || connBusy}
              placeholder="https://your-asap-gateway.example"
              autoComplete="url"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" disabled={!identityReady || connected || connBusy} onClick={() => void onConnect()}>
              {connBusy ? "Connecting…" : "Connect agent"}
            </Button>
            {connected ? (
              <span className="text-xs text-emerald-400">Agent registered with provider.</span>
            ) : null}
          </div>
          {initError !== null ? <p className="text-destructive text-sm">Identity error: {initError}</p> : null}
          {connError !== null ? <p className="text-destructive text-sm">{connError}</p> : null}
          {!identityReady && initError === null ? (
            <p className="text-muted-foreground text-sm">Initializing host / agent in localStorage…</p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Chat</CardTitle>
          <CardDescription>
            Capabilities from <code className="text-xs">NEXT_PUBLIC_ASAP_CAPABILITIES</code>:{" "}
            {DEMO_CAPABILITIES.join(", ") || "(none)"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground text-sm leading-relaxed">
            Set <code className="text-xs">OPENAI_API_KEY</code> locally for Mastra-backed chat. Prefer HTTPS/TLS against real gateways; JWT signing over
            plaintext HTTP is insecure for multi-tenant production traffic.
          </p>

          <div className="max-h-80 space-y-2 overflow-y-auto rounded-md border p-3" aria-live="polite">
            {messages.map((m) => (
              <div
                key={m.id}
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[85%] rounded-lg border border-sky-500/40 bg-sky-500/10 px-3 py-2 text-sm whitespace-pre-wrap"
                    : "max-w-[85%] rounded-lg border border-border bg-card px-3 py-2 text-sm whitespace-pre-wrap"
                }
              >
                {textFromUiMessage(m)}
              </div>
            ))}
          </div>

          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(e) => void onSend(e)}>
            <Textarea
              className="min-h-12 flex-1"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={connected ? "Message the model (ASAP Mastra tools)…" : "Connect to the gateway first…"}
              disabled={chatDisabled}
              rows={2}
            />
            <Button type="submit" className="sm:mb-0" disabled={chatDisabled}>
              Send
            </Button>
          </form>
          {error !== undefined ? <p className="text-destructive text-sm">{error.message}</p> : null}
          {status === "streaming" ? <p className="text-muted-foreground text-sm">Streaming…</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
