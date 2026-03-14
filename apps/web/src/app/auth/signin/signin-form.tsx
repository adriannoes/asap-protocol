'use client';

import { signIn } from 'next-auth/react';
import { motion } from 'framer-motion';
import { Github } from 'lucide-react';
import { Button } from '@/components/ui/button';

type SignInFormProps = {
    callbackUrl: string;
};

export function SignInForm({ callbackUrl }: SignInFormProps) {
    return (
        <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 150, damping: 25 }}
        >
        <Button
            size="lg"
            className="w-full bg-white text-black hover:bg-zinc-200 gap-3 h-12 text-base font-medium"
            onClick={() => signIn('github', { callbackUrl })}
        >
            <Github className="h-5 w-5" />
            Sign in with GitHub
        </Button>
        </motion.div>
    );
}
