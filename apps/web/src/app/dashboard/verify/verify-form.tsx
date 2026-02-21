'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useState } from 'react';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import Link from 'next/link';
import { submitVerificationRequest } from './actions';
import type { VerificationFormValues } from '@/lib/github-issues';

const VerificationSchema = z.object({
    agent_id: z.string().min(1, 'Agent ID is required'),
    why_verified: z.string().min(1, 'Please explain why this agent should be verified'),
    running_since: z.string().min(1, 'Please indicate how long the agent has been running'),
    evidence: z.string().optional(),
    contact: z.string().optional(),
});

type VerificationFormInput = z.infer<typeof VerificationSchema>;

interface VerifyFormProps {
    defaultAgentId: string;
}

export function VerifyForm({ defaultAgentId }: VerifyFormProps) {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<{ success?: boolean; error?: string; issueUrl?: string } | null>(null);

    const form = useForm<VerificationFormInput>({
        resolver: zodResolver(VerificationSchema),
        defaultValues: {
            agent_id: defaultAgentId,
            why_verified: '',
            running_since: '',
            evidence: '',
            contact: '',
        },
    });

    async function onSubmit(values: VerificationFormInput) {
        setIsSubmitting(true);
        setResult(null);

        try {
            const payload: VerificationFormValues = {
                agent_id: values.agent_id,
                why_verified: values.why_verified,
                running_since: values.running_since,
            };
            if (values.evidence) payload.evidence = values.evidence;
            if (values.contact) payload.contact = values.contact;

            const response = await submitVerificationRequest(payload);

            if (response.success && response.issueUrl) {
                setResult({ success: true, issueUrl: response.issueUrl });
                form.reset({ ...form.getValues(), why_verified: '', running_since: '', evidence: '', contact: '' });
                window.open(response.issueUrl, '_blank', 'noopener,noreferrer');
            } else {
                setResult({ success: false, error: response.error ?? 'Request failed' });
            }
        } catch {
            setResult({ success: false, error: 'An unexpected error occurred.' });
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
                    <p>Your details are pre-filled. A new tab should have opened—click &quot;Submit new issue&quot; on GitHub to complete your verification request.</p>
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

                <FormField
                    control={form.control}
                    name="agent_id"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Agent ID (required)</FormLabel>
                            <FormControl>
                                <Input placeholder="urn:asap:agent:username:agent-name" {...field} readOnly className="bg-muted font-mono text-sm" />
                            </FormControl>
                            <FormDescription>
                                URN of the agent to verify. Must already be listed in the registry.
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="why_verified"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Why should this agent be verified? (required)</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="This agent has been running in production for 3 months with 99.5% uptime..."
                                    className="min-h-[100px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormDescription>
                                Brief justification: use case, uptime, adoption, or other trust signals.
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="running_since"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>How long has it been running? (required)</FormLabel>
                            <FormControl>
                                <Input placeholder="2 months" {...field} />
                            </FormControl>
                            <FormDescription>
                                Approximate duration (e.g. &quot;2 months&quot;, &quot;since 2025-01&quot;).
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="evidence"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Evidence of reliability (optional)</FormLabel>
                            <FormControl>
                                <Textarea
                                    placeholder="e.g. Uptime: https://status.example.com — Running since 2025-01"
                                    className="min-h-[80px]"
                                    {...field}
                                />
                            </FormControl>
                            <FormDescription>
                                Links to uptime stats, monitoring dashboards, or other evidence.
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="contact"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Contact info (optional)</FormLabel>
                            <FormControl>
                                <Input placeholder="@username or email@example.com" {...field} />
                            </FormControl>
                            <FormDescription>
                                How maintainers can reach you.
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="flex justify-end gap-4 pt-4 border-t">
                    <Button type="button" variant="ghost" asChild>
                        <Link href="/dashboard">Cancel</Link>
                    </Button>
                    <Button type="submit" disabled={isSubmitting} className="min-w-[180px]">
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Preparing...
                            </>
                        ) : (
                            'Open GitHub Issue'
                        )}
                    </Button>
                </div>
            </form>
        </Form>
    );
}
