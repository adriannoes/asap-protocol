import { Metadata } from 'next';
import { RegisterAgentForm } from '../dashboard/register/register-form';

export const metadata: Metadata = {
    title: 'Test Register Agent',
    description: 'Test page for agent registration form validation.',
};

export default function TestRegisterPage() {
    return (
        <div className="container mx-auto py-10 px-4 max-w-3xl">
            <div className="mb-8 border-b pb-6">
                <h1 className="text-3xl font-bold tracking-tight">Test Register New Agent</h1>
            </div>

            <RegisterAgentForm />
        </div>
    );
}
