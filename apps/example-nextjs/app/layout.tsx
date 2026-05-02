// Minimal demo layout: Suspense and error boundaries are intentionally omitted.
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASAP + Vercel AI (example)",
  description: "Reference Next.js app: LocalStorage host, provider connect, chat with ASAP tools.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
