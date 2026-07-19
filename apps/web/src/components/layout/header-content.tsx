'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Terminal, Workflow, Sparkles } from 'lucide-react';
import { AGENT_BUILDER_URL_WITH_FROM } from '@/lib/agent-builder-url';
import { signInWithGitHub, signInWithGitHubForAgentBuilder, signOutAction } from '@/actions/auth';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { MobileNav } from './mobile-nav';
import type { Session } from 'next-auth';

interface HeaderContentProps {
  session: Session | null;
}

export function HeaderContent({ session }: HeaderContentProps) {
  const pathname = usePathname();
  const isDashboardRoute = pathname?.startsWith('/dashboard') ?? false;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur supports-[backdrop-filter]:bg-zinc-950/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
        {/* Logo Left */}
        <div className="flex items-center gap-2">
          <Link
            href="/"
            aria-label="ASAP Protocol — home"
            className="flex items-center gap-1 text-white transition-colors hover:text-indigo-400 md:gap-2"
          >
            <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/10 p-1.5">
              <Terminal className="h-5 w-5 text-indigo-400" />
            </div>
            <span className="hidden text-lg font-bold tracking-tight md:inline">ASAP Protocol</span>
          </Link>
        </div>

        {/* Mobile Nav — hidden on dashboard routes (Sidebar provides nav) */}
        {!isDashboardRoute && (
          <div className="flex flex-1 justify-end md:hidden">
            <MobileNav session={session} />
          </div>
        )}

        {/* Center Nav — hidden on dashboard routes (Sidebar provides nav) */}
        {!isDashboardRoute && (
          <nav className="hidden items-center gap-8 md:flex">
            <Link
              href="/browse"
              className="text-sm font-medium text-zinc-400 transition-colors hover:text-white"
            >
              Registry
            </Link>
            <Link
              href="/demos"
              className="text-sm font-medium text-zinc-400 transition-colors hover:text-white"
            >
              Demos
            </Link>
            <Link
              href="/developer-experience"
              className="text-sm font-medium text-zinc-400 transition-colors hover:text-white"
            >
              Developers
            </Link>
            <Link
              href="https://github.com/asap-protocol/asap-protocol/tree/main/docs"
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-zinc-400 transition-colors hover:text-white"
            >
              Docs
            </Link>
            {session?.user && (
              <a
                href={AGENT_BUILDER_URL_WITH_FROM}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-400 transition-colors hover:text-white"
              >
                <Workflow className="h-3.5 w-3.5" />
                Agent Builder
              </a>
            )}
            {!session?.user && (
              <form action={signInWithGitHubForAgentBuilder}>
                <button
                  type="submit"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-400 transition-colors hover:text-indigo-300"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Build Agents
                </button>
              </form>
            )}
          </nav>
        )}

        {/* Right Auth/Actions — always visible */}
        <div className="flex items-center gap-4">
          {session?.user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  className="relative h-9 w-9 rounded-full ring-1 ring-zinc-800 transition-all hover:ring-indigo-500/50"
                >
                  <Avatar className="h-9 w-9">
                    <AvatarImage
                      src={session.user.image ?? undefined}
                      alt={session.user.name || 'User'}
                    />
                    <AvatarFallback className="bg-zinc-900 text-zinc-400">
                      {session.user.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-56 border-zinc-800 bg-zinc-950 text-zinc-300"
                align="end"
                forceMount
              >
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm leading-none font-medium text-white">
                      {session.user.name}
                    </p>
                    <p className="text-xs leading-none text-zinc-500">{session.user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-zinc-800" />
                <DropdownMenuItem
                  asChild
                  className="cursor-pointer focus:bg-zinc-900 focus:text-white"
                >
                  <Link href="/dashboard">Dashboard</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-zinc-800" />
                <DropdownMenuItem className="cursor-pointer p-0 focus:bg-zinc-900 focus:text-red-400">
                  <form className="w-full" action={signOutAction}>
                    <button className="w-full px-2 py-1.5 text-left" type="submit">
                      Log out
                    </button>
                  </form>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <form action={signInWithGitHub}>
              <Button
                type="submit"
                variant="outline"
                className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white"
              >
                Connect / Login
              </Button>
            </form>
          )}
        </div>
      </div>
    </header>
  );
}
