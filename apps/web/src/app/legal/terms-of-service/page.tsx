import type { Metadata } from 'next';
import { Terminal } from 'lucide-react';

export const metadata: Metadata = {
    title: 'Terms of Service | ASAP Protocol',
    description:
        'Terms of Service for the ASAP Protocol network regarding usage, SLA guarantees, and liability limitations.',
};

export default function TermsOfServicePage() {
    return (
        <div className="flex flex-col min-h-[70vh] items-center justify-center p-6 text-center">
            <div className="bg-indigo-500/10 p-4 rounded-2xl border border-indigo-500/20 mb-6">
                <Terminal className="w-10 h-10 text-indigo-400" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-4">Terms of Service</h1>
            <p className="max-w-xl text-zinc-400 text-lg leading-relaxed">
                The ASAP Protocol network is currently in developer beta.
                Full Terms of Service regarding network usage, SLA guarantees, and liability limitations are being drafted.
            </p>
            <div className="mt-8 text-sm text-zinc-600 font-mono">
                Draft v2.0.0-beta
            </div>
        </div>
    );
}
