"use client";

import { AsapDemo } from "@/components/asap-demo";

export function ExampleHome() {
  return (
    <>
      <h1>ASAP Protocol · Next.js example</h1>
      <p className="description">
        Registers an ASAP host in <code>localStorage</code>, connects an agent to your gateway, then chats via the
        Vercel AI SDK with ASAP capabilities exposed as tools.
      </p>
      <AsapDemo />
    </>
  );
}
