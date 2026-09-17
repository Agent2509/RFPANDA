import { RouteGuard } from "@/components/auth/RouteGuard";
import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta-sans',
});

export const metadata: Metadata = {
  title: 'RFPANDA — Smart Document AI',
  description: 'Upload documents and get instant AI-powered answers with page-level citations.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`min-h-screen bg-[#FAFAF8] font-sans ${plusJakartaSans.variable}`}>
        <RouteGuard>{children}</RouteGuard>
      </body>
    </html>
  );
}
