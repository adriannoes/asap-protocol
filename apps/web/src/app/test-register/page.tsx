import { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { RegisterAgentForm } from '../dashboard/register/register-form';

export const metadata: Metadata = {
    title: 'Test Register Agent',
    description: 'Test page for agent registration form validation.',
};

export default function TestRegisterPage() {
    // Block access in production — this page is only for local development testing
    if (process.env.NODE_ENV === 'production') {
        redirect('/dashboard/register');
    }

    return (
        <div className="container mx-auto py-10 px-4 max-w-3xl">
            <div className="mb-8 border-b pb-6">
                <h1 className="text-3xl font-bold tracking-tight">Test Register New Agent</h1>
                <p className="text-sm text-muted-foreground mt-2">
                    Development-only page. Redirects to the real registration form in production.
                </p>
            </div>

            <RegisterAgentForm />
        </div>
    );
}
