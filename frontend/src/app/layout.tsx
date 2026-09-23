import { RouteGuard } from "@/components/auth/RouteGuard";
import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta-sans',
});

export const metadata: Metadata = {
  title: 'RFPANDA — Ask your documents anything',
  description: 'Upload documents and get instant, cited answers grounded in your own files.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={plusJakartaSans.variable}>
      <body className="min-h-screen bg-canvas font-sans text-zinc-900">
        <RouteGuard>{children}</RouteGuard>
      </body>
    </html>
  );
}
