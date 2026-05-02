'use client';

import { useCallback, useState } from 'react';
import { Check, ChevronDown, Code2, Copy } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface AgentConnectActionsProps {
    endpoint: string | undefined | null;
}

/**
 * Sidebar integration panel: primary action is copying the endpoint (concrete).
 * Snippet jump is a text link on the same page — avoids a misleading "connect" CTA
 * that reads like navigation to another app or OAuth flow.
 */
export function AgentConnectActions({ endpoint }: AgentConnectActionsProps) {
    const [copied, setCopied] = useState(false);

    const copyEndpoint = useCallback(async () => {
        if (!endpoint) return;
        await navigator.clipboard.writeText(endpoint);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2000);
    }, [endpoint]);

    return (
        <div className="flex flex-col gap-3 w-full">
            <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Integration
                </p>
                <p className="mt-1 text-xs text-muted-foreground/90 leading-snug">
                    Copy the ASAP endpoint URL or open ready-to-use integration examples below.
                </p>
            </div>
            <Button
                type="button"
                className="w-full gap-2 font-semibold shadow-md"
                size="lg"
                disabled={!endpoint}
                onClick={() => void copyEndpoint()}
            >
                {copied ? (
                    <>
                        <Check className="w-4 h-4 text-emerald-500" /> Copied to clipboard
                    </>
                ) : (
                    <>
                        <Copy className="w-4 h-4" /> Copy ASAP endpoint
                    </>
                )}
            </Button>
            <a
                href="#integration"
                className="inline-flex w-full items-center justify-center gap-1.5 rounded-md py-2 text-sm text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background"
            >
                <Code2 className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
                View integration snippets
                <ChevronDown className="h-4 w-4 shrink-0 opacity-60" aria-hidden />
            </a>
        </div>
    );
}
