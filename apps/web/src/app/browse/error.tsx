'use client';

export default function Error({
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- Next.js error boundary requires error prop
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <div className="container mx-auto py-10 px-4 text-center">
            <h2 className="text-xl font-semibold text-destructive mb-2">Something went wrong</h2>
            <p className="text-muted-foreground text-sm mb-6">We could not load the registry. Please try again.</p>
            <button
                type="button"
                onClick={() => reset()}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
                Try again
            </button>
        </div>
    );
}
