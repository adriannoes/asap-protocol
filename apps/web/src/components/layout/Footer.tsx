import Link from 'next/link';
import { Github, Book, Terminal } from 'lucide-react';

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-900 bg-zinc-950 py-16 text-zinc-400">
      <div className="container mx-auto px-4 md:px-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-8 justify-between">

          {/* Protocol Column */}
          <div className="flex flex-col gap-4">
            <h4 className="font-semibold text-white tracking-tight">Protocol</h4>
            <div className="flex flex-col gap-3">
              <Link
                href="https://github.com/adriannoes/asap-protocol"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-sm transition-colors hover:text-white"
              >
                <Github className="h-4 w-4" />
                <span>GitHub Repository</span>
              </Link>
              <Link
                href="https://github.com/adriannoes/asap-protocol/tree/main/docs"
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-sm transition-colors hover:text-white"
              >
                <Book className="h-4 w-4" />
                <span>Documentation</span>
              </Link>
              <Link
                href="/developer-experience"
                className="flex items-center gap-2 text-sm transition-colors hover:text-white"
              >
                <Terminal className="h-4 w-4" />
                <span>Developer Experience</span>
              </Link>
            </div>
          </div>

          {/* Legal Column */}
          <div className="flex flex-col gap-4">
            <h4 className="font-semibold text-white tracking-tight">Legal & Compliance</h4>
            <div className="flex flex-col gap-3">
              <Link
                href="/legal/privacy-policy"
                className="text-sm transition-colors hover:text-white"
              >
                Privacy Policy
              </Link>
              <Link
                href="/legal/terms-of-service"
                className="text-sm transition-colors hover:text-white"
              >
                Terms of Service
              </Link>
              <Link
                href="https://github.com/adriannoes/asap-protocol/blob/main/LICENSE"
                target="_blank"
                rel="noreferrer"
                className="text-sm transition-colors hover:text-white"
              >
                Apache 2.0 License
              </Link>
            </div>
          </div>

        </div>

        <div className="mt-16 pt-8 border-t border-zinc-900 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-zinc-600">
          <p>© {new Date().getFullYear()} ASAP Protocol Authors.</p>
          <div className="flex items-center gap-4">
            <span>From agents, for agents. Delivering reliability, as soon as possible.</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
