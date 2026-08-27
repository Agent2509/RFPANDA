import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ApexTender v2.0 — Production-Grade RAG RFP Engine',
  description: 'Enterprise RFP Analysis platform optimized for Free-Tier Cloud Infrastructure (Supabase pgvector, Voyage AI, Groq Llama 3, FastAPI)',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 font-sans">{children}</body>
    </html>
  );
}
