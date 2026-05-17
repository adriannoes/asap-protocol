import { ChatShell } from "@/components/chat-shell";
import { MastraChatDemo } from "@/components/mastra-chat-demo";

export default function Page() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">ASAP Protocol · Mastra + Next.js</h1>
      <p className="text-muted-foreground mt-2 leading-relaxed">
        Registers an ASAP identity in localStorage, connects to your gateway, then chats through a Mastra Agent with ASAP
        capabilities exposed as Mastra tools. Streams assistant text with the Vercel AI SDK UI protocol.
      </p>
      <ChatShell>
        <MastraChatDemo />
      </ChatShell>
    </main>
  );
}
