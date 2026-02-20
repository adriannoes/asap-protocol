'use client';

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
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
import { submitAgentRegistration } from "./actions";

// Form validation schema matching 2.4.2 requirements
const formSchema = z.object({
    name: z.string().min(3).max(50).regex(/^[a-z0-9-]+$/, {
        message: "Name can only contain lowercase letters, numbers, and hyphens (slug-friendly).",
    }),
    description: z.string().min(10).max(200),
    manifest_url: z.string().url({ message: "Must be a valid URL starting with http:// or https://" }),
    endpoint_http: z.string().url({ message: "Must be a valid URL" }),
    endpoint_ws: z.string().url().optional().or(z.literal('')),
    skills: z.string().min(1, { message: "At least one skill is required" }), // Comma separated for now
});

export function RegisterAgentForm() {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<{ success?: boolean; error?: string; prUrl?: string } | null>(null);

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            description: "",
            manifest_url: "",
            endpoint_http: "",
            endpoint_ws: "",
            skills: "",
        },
    });

    async function onSubmit(values: z.infer<typeof formSchema>) {
        setIsSubmitting(true);
        setResult(null);

        try {
            // Server action call (defined in actions.ts)
            const response = await submitAgentRegistration(values);

            if (response.success) {
                setResult({ success: true, prUrl: response.prUrl });
                form.reset();
            } else {
                setResult({ success: false, error: response.error });
            }
        } catch (error) {
            setResult({ success: false, error: "An unexpected error occurred during submission." });
        } finally {
            setIsSubmitting(false);
        }
    }

    if (result?.success) {
        return (
            <Alert className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                <CheckCircle2 className="h-4 w-4 stroke-emerald-500" />
                <AlertTitle>Registration Submitted!</AlertTitle>
                <AlertDescription className="mt-2 space-y-4">
                    <p>Your agent registration has been submitted as a Pull Request to the registry.</p>
                    {result.prUrl && (
                        <Button asChild variant="outline" className="border-emerald-500/20 text-emerald-500 hover:bg-emerald-500/20">
                            <a href={result.prUrl} target="_blank" rel="noopener noreferrer">
                                View Pull Request on GitHub
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
                                <FormLabel>Agent Slug Name</FormLabel>
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
                                <FormLabel>Manifest URL</FormLabel>
                                <FormControl>
                                    <Input placeholder="https://api.myagent.com/asap/manifest" {...field} />
                                </FormControl>
                                <FormDescription>
                                    Public URL to fetch your agent's manifest.json
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
                            <FormLabel>Short Description</FormLabel>
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
                                <FormLabel>HTTP Endpoint</FormLabel>
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
                                <FormLabel>WebSocket Endpoint (Optional)</FormLabel>
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
                            <FormLabel>Skills (Comma separated)</FormLabel>
                            <FormControl>
                                <Input placeholder="search, summarization, analysis" {...field} />
                            </FormControl>
                            <FormDescription>
                                Tags identifying the capabilities of your agent. Example: search, web_automation
                            </FormDescription>
                            <FormMessage />
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
