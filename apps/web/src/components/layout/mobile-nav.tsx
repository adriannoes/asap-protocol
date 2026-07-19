'use client';

import { useState } from 'react';
import Link from 'next/link';
import type { Session } from 'next-auth';
import { Menu, Terminal, Workflow, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { AGENT_BUILDER_URL_WITH_FROM } from '@/lib/agent-builder-url';

const BUILD_AGENTS_CALLBACK_URL = encodeURIComponent(AGENT_BUILDER_URL_WITH_FROM);

export function MobileNav({ session }: { session: Session | null }) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="text-zinc-400 hover:text-white md:hidden">
          <Menu className="h-6 w-6" />
          <span className="sr-only">Toggle Menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-[300px] border-zinc-800 bg-zinc-950 text-zinc-300 sm:w-[400px]"
      >
        <SheetHeader className="border-b border-zinc-800 pb-6">
          <SheetTitle asChild>
            <Link
              href="/"
              className="flex items-center gap-2 text-white"
              onClick={() => setOpen(false)}
            >
              <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/10 p-1.5">
                <Terminal className="h-5 w-5 text-indigo-400" />
              </div>
              <span className="text-lg font-bold tracking-tight">ASAP Protocol</span>
            </Link>
          </SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-4 py-8">
          <Link
            href="/browse"
            onClick={() => setOpen(false)}
            className="text-lg font-medium text-zinc-400 transition-colors hover:text-white"
          >
            Registry
          </Link>
          <Link
            href="/demos"
            onClick={() => setOpen(false)}
            className="text-lg font-medium text-zinc-400 transition-colors hover:text-white"
          >
            Demos
          </Link>
          <Link
            href="/developer-experience"
            onClick={() => setOpen(false)}
            className="text-lg font-medium text-zinc-400 transition-colors hover:text-white"
          >
            Developer Experience
          </Link>
          <Link
            href="https://github.com/asap-protocol/asap-protocol/tree/main/docs"
            target="_blank"
            rel="noreferrer"
            onClick={() => setOpen(false)}
            className="text-lg font-medium text-zinc-400 transition-colors hover:text-white"
          >
            Docs
          </Link>
          {session?.user ? (
            <a
              href={AGENT_BUILDER_URL_WITH_FROM}
              onClick={() => setOpen(false)}
              className="inline-flex items-center gap-1.5 text-lg font-medium text-zinc-400 transition-colors hover:text-white"
            >
              <Workflow className="h-4 w-4" />
              Agent Builder
            </a>
          ) : (
            <a
              href={`/api/auth/signin?callbackUrl=${BUILD_AGENTS_CALLBACK_URL}`}
              onClick={() => setOpen(false)}
              className="inline-flex items-center gap-1.5 text-lg font-medium text-indigo-400 transition-colors hover:text-indigo-300"
            >
              <Sparkles className="h-4 w-4" />
              Build Agents
            </a>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
