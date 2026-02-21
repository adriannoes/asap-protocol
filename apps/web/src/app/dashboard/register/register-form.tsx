'use client';

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import Link from "next/link";
import { ManifestSchema, type ManifestFormValues } from "@/lib/register-schema";
import { submitAgentRegistration } from "./actions";

const BUILT_WITH_OPTIONS = ['', 'CrewAI', 'OpenClaw', 'LangChain', 'AutoGen', 'Other'] as const;

export function RegisterAgentForm() {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<{ success?: boolean; error?: string; issueUrl?: string } | null>(null);

    const form = useForm<ManifestFormValues>({
        resolver: zodResolver(ManifestSchema),
        defaultValues: {
            name: "",
            description: "",
            manifest_url: "",
            endpoint_http: "",
            endpoint_ws: "",
            skills: "",
            built_with: "",
            repository_url: "",
            documentation_url: "",
            confirm: false,
        },
    });

    async function onSubmit(values: ManifestFormValues) {
        setIsSubmitting(true);
        setResult(null);

        try {
            // Server action call (defined in actions.ts)
            const response = await submitAgentRegistration(values);

            if (response.success && response.issueUrl) {
                setResult({ success: true, issueUrl: response.issueUrl });
                form.reset();
                window.open(response.issueUrl, '_blank', 'noopener,noreferrer');
            } else {
                setResult({ success: false, error: response.error });
            }
        } catch {
            setResult({ success: false, error: "An unexpected error occurred during submission." });
        } finally {
            setIsSubmitting(false);
        }
    }

    if (result?.success) {
        return (
            <Alert className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                <CheckCircle2 className="h-4 w-4 stroke-emerald-500" />
                <AlertTitle>Open GitHub to submit</AlertTitle>
                <AlertDescription className="mt-2 space-y-4">
                    <p>Your details are pre-filled. A new tab should have opened—click &quot;Submit new issue&quot; on GitHub to complete registration.</p>
                    {result.issueUrl && (
                        <Button asChild variant="outline" className="border-emerald-500/20 text-emerald-500 hover:bg-emerald-500/20">
                            <a href={result.issueUrl} target="_blank" rel="noopener noreferrer">
                                Open GitHub Issue
                            </a>
                        </Button>
                    )}
                    <div className="mt-4">
                        <Button asChild variant="ghost" className="text-emerald-500 hover:bg-emerald-500/10">
                            <Link href="/dashboard">Return to Dashboard</Link>
                        </Button>
                    </div>
                </AlertDescription>
            </Alert>
        );
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                {result?.error && (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Error</AlertTitle>
                        <AlertDescription>{result.error}</AlertDescription>
                    </Alert>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                        control={form.control}
                        name="name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Agent Slug Name (required)</FormLabel>
                                <FormControl>
                                    <Input placeholder="my-awesome-agent" {...field} />
                                </FormControl>
                                <FormDescription>
                                    Unique, URL-friendly identifier for your agent.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="manifest_url"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Manifest URL (required)</FormLabel>
                                <FormControl>
                                    <Input placeholder="https://api.myagent.com/asap/manifest" {...field} />
                                </FormControl>
                                <FormDescription>
                                    Public URL to fetch your agent&apos;s manifest.json
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Short Description (required)</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="Briefly describe what your agent does and how it's used..."
                                    className="resize-none"
                                    {...field}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4 border rounded-lg bg-card/50">
                    <FormField
                        control={form.control}
                        name="endpoint_http"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>HTTP Endpoint (required)</FormLabel>
                                <FormControl>
                                    <Input placeholder="https://api.myagent.com/asap" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control}
                        name="endpoint_ws"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>WebSocket Endpoint (optional)</FormLabel>
                                <FormControl>
                                    <Input placeholder="wss://api.myagent.com/asap/ws" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="skills"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Skills (required, comma separated)</FormLabel>
                            <FormControl>
                                <Input placeholder="web_research, summarization" {...field} />
                            </FormControl>
                            <FormDescription>
                                Skill identifiers your agent supports. Example: web_research, summarization
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="built_with"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Built with (framework)</FormLabel>
                            <FormControl>
                                <select
                                    {...field}
                                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring md:text-sm"
                                >
                                    {BUILT_WITH_OPTIONS.map((opt) => (
                                        <option key={opt || 'none'} value={opt}>
                                            {opt || '—'}
                                        </option>
                                    ))}
                                </select>
                            </FormControl>
                            <FormDescription>
                                Framework or platform used to build this agent (optional). Helps discovery.
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                        control={form.control}
                        name="repository_url"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Repository URL (optional)</FormLabel>
                                <FormControl>
                                    <Input placeholder="https://github.com/username/agent-repo" {...field} />
                                </FormControl>
                                <FormDescription>
                                    Link to the agent source code. Helps trust and verification.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="documentation_url"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Documentation URL (optional)</FormLabel>
                                <FormControl>
                                    <Input placeholder="https://docs.example.com/agent" {...field} />
                                </FormControl>
                                <FormDescription>
                                    Link to docs on how to use this agent.
                                </FormDescription>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                <FormField
                    control={form.control}
                    name="confirm"
                    render={({ field }) => (
                        <FormItem>
                            <div className="flex items-start gap-3 rounded-lg border p-4">
                                <FormControl>
                                    <input
                                        id="confirm-registration"
                                        type="checkbox"
                                        checked={Boolean(field.value)}
                                        onChange={(e) => field.onChange(e.target.checked)}
                                        className="h-4 w-4 rounded border-input mt-0.5"
                                    />
                                </FormControl>
                                <div className="space-y-1">
                                    <FormLabel htmlFor="confirm-registration" className="cursor-pointer font-normal">
                                        I confirm that the manifest URL is publicly accessible (no auth) and that the HTTP/WebSocket endpoints above match my manifest. (required)
                                    </FormLabel>
                                    <FormMessage />
                                </div>
                            </div>
                        </FormItem>
                    )}
                />

                <div className="flex justify-end pt-4 border-t">
                    <Button type="button" variant="ghost" asChild className="mr-4">
                        <Link href="/dashboard">Cancel</Link>
                    </Button>
                    <Button type="submit" disabled={isSubmitting} className="min-w-[150px]">
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            "Submit Registration"
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    );
}
