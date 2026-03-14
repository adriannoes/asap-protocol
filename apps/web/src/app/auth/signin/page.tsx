import { Metadata } from 'next';
import Link from 'next/link';
import { Terminal } from 'lucide-react';
import { SignInForm } from './signin-form';
import { CanvasBg } from '@/components/ui/canvas-bg';
import { GlassContainer } from '@/components/ui/glass-container';

export const metadata: Metadata = {
    title: 'Sign in | ASAP Protocol',
    description: 'Sign in with GitHub to access the ASAP Protocol developer dashboard.',
};

type PageProps = {
    searchParams: Promise<{ callbackUrl?: string }>;
};

export default async function SignInPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const callbackUrl = params.callbackUrl ?? '/dashboard';

    return (
        <main className="relative flex min-h-[calc(100vh-8rem)] flex-col items-center justify-center px-4 py-16 overflow-hidden">
            <CanvasBg />
            <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-8 text-center">
                <Link
                    href="/"
                    className="flex items-center gap-2 text-white hover:text-indigo-400 transition-colors"
                >
                    <div className="bg-indigo-500/10 p-2 rounded-lg border border-indigo-500/20">
                        <Terminal className="h-8 w-8 text-indigo-400" />
                    </div>
                    <span className="font-bold text-xl tracking-tight">ASAP Protocol</span>
                </Link>

                <div className="space-y-4">
                    <h1 className="text-2xl font-semibold tracking-tight text-white">
                        Sign in to continue
                    </h1>
                    <p className="text-zinc-400 text-sm leading-relaxed max-w-sm mx-auto">
                        Use your GitHub account to access the developer dashboard, register agents,
                        and manage your integrations with the ASAP Protocol marketplace.
                    </p>
                </div>

                <GlassContainer className="p-8 w-full">
                    <SignInForm callbackUrl={callbackUrl} />
                </GlassContainer>

                <p className="text-xs text-zinc-500">
                    By signing in, you agree to our{' '}
                    <a
                        href="https://github.com/adriannoes/asap-protocol/blob/main/LICENSE"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-zinc-400 hover:text-indigo-400 underline underline-offset-2"
                    >
                        Apache 2.0 License
                    </a>{' '}
                    and{' '}
                    <a
                        href="https://github.com/adriannoes/asap-protocol/blob/main/SECURITY.md"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-zinc-400 hover:text-indigo-400 underline underline-offset-2"
                    >
                        Security Policy
                    </a>
                    .
                </p>
            </div>
        </main>
    );
}
