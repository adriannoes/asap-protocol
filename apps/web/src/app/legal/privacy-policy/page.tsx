import type { Metadata } from 'next';
import { Terminal } from 'lucide-react';

export const metadata: Metadata = {
    title: 'Privacy Policy | ASAP Protocol',
    description:
        'Privacy policy for the ASAP Protocol network regarding registry telemetry and GitHub App authorizations.',
};

export default function PrivacyPolicyPage() {
    return (
        <div className="flex flex-col min-h-[70vh] items-center justify-center p-6 text-center">
            <div className="bg-indigo-500/10 p-4 rounded-2xl border border-indigo-500/20 mb-6">
                <Terminal className="w-10 h-10 text-indigo-400" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-4">Privacy Policy</h1>
            <p className="max-w-xl text-zinc-400 text-lg leading-relaxed">
                The ASAP Protocol network is currently in developer beta.
                Full privacy policy documentation regarding registry telemetry and GitHub App authorizations is being drafted.
            </p>
            <div className="mt-8 text-sm text-zinc-600 font-mono">
                Draft v2.0.0-beta
            </div>
        </div>
    );
}
