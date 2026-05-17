"use client";

import { Component, type ErrorInfo, type ReactNode, Suspense } from "react";

type ErrorBoundaryState = { error: Error | null };

export class ChatErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("example-mastra UI error:", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error !== null) {
      return (
        <div className="border-destructive/50 bg-destructive/10 text-destructive rounded-lg border p-4 text-sm">
          <p className="font-semibold">Something went wrong loading the chat demo.</p>
          <p className="mt-2 text-xs">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export function SuspenseFallback(): ReactNode {
  return <p className="text-muted-foreground text-sm">Loading chat shell…</p>;
}

export function ChatShell({ children }: { children: ReactNode }): ReactNode {
  return (
    <ChatErrorBoundary>
      <Suspense fallback={<SuspenseFallback />}>{children}</Suspense>
    </ChatErrorBoundary>
  );
}
