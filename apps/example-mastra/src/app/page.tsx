import { MastraChatDemo } from "@/components/mastra-chat-demo";

export default function Page() {
  return (
    <>
      <h1>ASAP Protocol · Mastra + Next.js</h1>
      <p className="description">
        Registers an ASAP identity in localStorage, connects to your gateway, then chats through a Mastra Agent with ASAP
        capabilities exposed as Mastra tools. Streams assistant text with the Vercel AI SDK UI protocol.
      </p>
      <MastraChatDemo />
    </>
  );
}
