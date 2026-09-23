'use client';

import React from 'react';
import { Button } from '@/components/ui';
import { ArrowRight, FileText, Search, ShieldCheck, Sparkles, Quote } from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-zinc-900">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-zinc-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-zinc-900 text-lg shadow-sm">🐼</span>
            <span className="text-base font-extrabold tracking-tight">RFPANDA</span>
          </Link>
          <nav className="flex items-center gap-2">
            <Link href="/login">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link href="/signup">
              <Button size="sm" className="gap-1.5">
                Get started <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden px-5 py-20 md:py-28">
          <div className="pointer-events-none absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]" />
          <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[42rem] -translate-x-1/2 rounded-full bg-brand-300/30 blur-3xl" />

          <div className="relative mx-auto flex max-w-3xl flex-col items-center text-center animate-fade-up">
            <span className="chip border-brand-200 bg-brand-50 text-brand-700">
              <Sparkles className="h-3.5 w-3.5" />
              Grounded document AI
            </span>

            <h1 className="mt-6 text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl md:text-6xl">
              Ask your documents
              <span className="bg-gradient-to-r from-brand-600 to-brand-400 bg-clip-text text-transparent"> anything</span>
            </h1>

            <p className="mt-5 max-w-xl text-base text-zinc-500 md:text-lg">
              Upload PDFs and reports, then get instant answers with exact page citations. No hallucinations — every
              claim is grounded in your files.
            </p>

            <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row">
              <Link href="/signup">
                <Button size="lg" className="gap-2">
                  Get started free <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/login">
                <Button size="lg" variant="outline">Sign in</Button>
              </Link>
            </div>

            <p className="mt-4 text-xs text-zinc-400">No credit card required · PDF, DOCX, TXT, MD</p>
          </div>
        </section>

        {/* Features */}
        <section className="border-y border-zinc-200/70 bg-white px-5 py-20">
          <div className="mx-auto grid max-w-6xl grid-cols-1 gap-5 md:grid-cols-3">
            {[
              {
                icon: <Search className="h-5 w-5" />,
                title: 'Semantic search',
                body: 'Find the right passage across hundreds of pages in milliseconds using vector similarity.',
              },
              {
                icon: <ShieldCheck className="h-5 w-5" />,
                title: 'Grounded answers',
                body: 'Responses are generated only from retrieved context, so you can trust what you read.',
              },
              {
                icon: <FileText className="h-5 w-5" />,
                title: 'Page-level citations',
                body: 'Every answer links back to the exact document, page, and excerpt it came from.',
              },
            ].map((f) => (
              <div
                key={f.title}
                className="group rounded-2xl border border-zinc-200/80 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:shadow-card"
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-600 group-hover:text-white">
                  {f.icon}
                </span>
                <h3 className="mt-4 text-base font-bold text-zinc-900">{f.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-zinc-500">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Quote / stats strip */}
        <section className="px-5 py-20">
          <div className="mx-auto flex max-w-4xl flex-col items-center rounded-3xl border border-zinc-200/80 bg-white p-10 text-center shadow-soft">
            <Quote className="h-7 w-7 text-brand-300" />
            <p className="mt-4 max-w-2xl text-lg font-medium leading-relaxed text-zinc-700">
              “I dropped in a 500-page report and got a precise, cited summary in seconds instead of skimming for an
              afternoon.”
            </p>
            <div className="mt-6 grid grid-cols-3 gap-8 border-t border-zinc-100 pt-6 text-center">
              {[
                ['50MB', 'max file size'],
                ['1024-d', 'embeddings'],
                ['p. X', 'citations'],
              ].map(([value, label]) => (
                <div key={label}>
                  <p className="text-xl font-extrabold tracking-tight text-zinc-900">{value}</p>
                  <p className="text-xs text-zinc-400">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-200/70 bg-white py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 text-xs text-zinc-400 sm:flex-row">
          <span className="flex items-center gap-2">
            <span>🐼</span> © 2026 RFPANDA
          </span>
          <span>Built for people who’d rather ask than skim.</span>
        </div>
      </footer>
    </div>
  );
}
