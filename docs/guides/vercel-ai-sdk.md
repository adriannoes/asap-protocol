# Vercel AI SDK Integration

This guide describes how to use ASAP agents with the [Vercel AI SDK](https://sdk.vercel.ai) in Next.js/React applications. The Python adapter exposes HTTP endpoints that return tool definitions in JSON Schema format, which the frontend uses with `tool({ parameters: jsonSchema(...) })`.

## Overview

- **Python backend**: FastAPI router with `GET /tools` (tool definitions) and `POST /invoke` (agent execution).
- **Frontend**: Next.js API route or server component fetches tool definitions and wires `execute` to call the Python backend.

## Backend Setup

### 1. Mount the ASAP tools router

```python
from fastapi import FastAPI
from asap.integrations.vercel_ai import create_asap_tools_router

app = FastAPI()
app.include_router(
    create_asap_tools_router(),
    prefix="/api/asap",
    tags=["asap-tools"],
)
```

### 2. Optional: whitelist specific agents

Expose specific agents as top-level tools with their own schemas:

```python
app.include_router(
    create_asap_tools_router(
        whitelist_urns=["urn:asap:agent:weather", "urn:asap:agent:summarizer"],
    ),
    prefix="/api/asap",
    tags=["asap-tools"],
)
```

### 3. Run the backend

```bash
uvicorn your_app:app --reload
```

## Frontend Setup (Next.js)

### 1. Fetch tool definitions

```ts
// app/api/asap/tools/route.ts
import { NextResponse } from "next/server";

const ASAP_BACKEND = process.env.ASAP_BACKEND_URL || "http://localhost:8000";

export async function GET() {
  const res = await fetch(`${ASAP_BACKEND}/api/asap/tools`);
  const data = await res.json();
  return NextResponse.json(data);
}
```

### 2. Define tools with jsonSchema

```ts
// lib/asap-tools.ts
import { tool } from "ai";
import { jsonSchema } from "ai";

const ASAP_BACKEND = process.env.ASAP_BACKEND_URL || "http://localhost:8000";

export async function getAsapTools(): Promise<Record<string, ReturnType<typeof tool>>> {
  const res = await fetch(`${ASAP_BACKEND}/api/asap/tools`);
  const { tools } = await res.json();
  const toolMap: Record<string, ReturnType<typeof tool>> = {};

  for (const def of tools) {
    toolMap[def.name] = tool({
      description: def.description,
      parameters: jsonSchema(def.parameters),
      execute: async (args) => {
        const payload = def.urn
          ? { urn: def.urn, payload: { input: args } }
          : { urn: args.urn, payload: args.payload };
        const inv = await fetch(`${ASAP_BACKEND}/api/asap/invoke`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await inv.json();
        if (data.error) throw new Error(data.error);
        return data.result;
      },
    });
  }
  return toolMap;
}
```

### 3. Use in streamText or generateText

```ts
// app/api/chat/route.ts
import { streamText } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { getAsapTools } from "@/lib/asap-tools";

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages } = await req.json();
  const tools = await getAsapTools();

  const result = streamText({
    model: createOpenAI({ apiKey: process.env.OPENAI_API_KEY })("gpt-4o"),
    messages,
    tools,
    maxSteps: 5,
  });

  return result.toDataStreamResponse();
}
```

## API Reference

### GET /api/asap/tools

Returns tool definitions for Vercel AI SDK:

```json
{
  "tools": [
    {
      "name": "asap_invoke",
      "description": "Invoke an ASAP agent by URN with the given payload.",
      "parameters": {
        "type": "object",
        "properties": {
          "urn": { "type": "string", "description": "ASAP agent URN" },
          "payload": { "type": "object", "description": "Skill input payload" }
        },
        "required": ["urn", "payload"]
      },
      "urn": null
    }
  ]
}
```

For whitelist tools, `urn` is set so the frontend knows which URN to pass to `/invoke`.

### POST /api/asap/invoke

Invoke an agent:

```json
// Request
{ "urn": "urn:asap:agent:example", "payload": { "message": "hello" } }

// Response (success)
{ "result": { "output": "..." } }

// Response (error)
{ "error": "Agent not found in registry: ..." }
```

The `payload` is the skill input; the backend builds the full TaskRequest (conversation_id, skill_id, input) automatically.

### GET /api/asap/discover

Search the Lite Registry:

```
GET /api/asap/discover?query=weather
```

Returns a JSON array of matching `RegistryEntry` objects.

## Environment Variables

| Variable         | Description                          | Default                    |
|------------------|--------------------------------------|----------------------------|
| ASAP_BACKEND_URL | Python backend URL (frontend)        | http://localhost:8000      |
| ASAP_REGISTRY_URL| Lite Registry URL (backend)           | Official GitHub Pages URL  |
| ASAP_AUTH_TOKEN  | Bearer token for agent endpoints     | -                         |
