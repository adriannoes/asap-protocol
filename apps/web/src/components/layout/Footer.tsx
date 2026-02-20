import Link from 'next/link';
import { Github, Book } from 'lucide-react';

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-900 bg-zinc-950 py-12 text-zinc-400">
      <div className="container mx-auto flex flex-col items-center justify-center gap-6 px-4 md:px-6">
        <div className="flex gap-4">
          <Link
            href="https://github.com/adriannoes/asap-protocol"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 transition-colors hover:text-white"
          >
            <Github className="h-5 w-5" />
            <span>GitHub</span>
          </Link>
          <Link
            href="https://github.com/adriannoes/asap-protocol/tree/main/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 transition-colors hover:text-white"
          >
            <Book className="h-5 w-5" />
            <span>Documentation</span>
          </Link>
        </div>
        <div className="text-center text-sm text-zinc-600">
          <p>© {new Date().getFullYear()} ASAP Protocol. Open Source under MIT License.</p>
        </div>
      </div>
    </footer>
  );
}
