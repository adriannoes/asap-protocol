import { Metadata } from 'next';
import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import { RegisterAgentForm } from './register-form';

export const metadata: Metadata = {
    title: 'Register Agent | Developer Dashboard',
    description: 'Register a new autonomous agent on the ASAP Protocol.',
};

export default async function RegisterAgentPage() {
    const session = await auth();

    if (!session?.user) {
        redirect('/');
    }

    return (
        <div className="container mx-auto py-10 px-4 max-w-3xl">
            <div className="mb-8 border-b pb-6">
                <h1 className="text-3xl font-bold tracking-tight">Register New Agent</h1>
                <p className="text-muted-foreground mt-2">
                    Publish your agent to the ASAP Protocol registry. You will be taken to GitHub to submit
                    a pre-filled registration issue; a GitHub Action will validate and add your agent to the registry.
                </p>
            </div>

            <RegisterAgentForm />
        </div>
    );
}
