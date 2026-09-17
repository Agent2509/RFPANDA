'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui';
import { Zap, Search, ArrowRight, FileText, CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-[#FAFAF8] text-stone-800 font-sans">
      <header className="flex h-16 items-center justify-between border-b border-stone-200 bg-white/80 px-6 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🐼</span>
          <h1 className="text-xl font-bold tracking-tight text-stone-900">
            RFPANDA
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="outline" className="text-emerald-600 border-stone-200 bg-white hover:bg-stone-50 rounded-full">
              Sign In / Enter App
            </Button>
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <section className="relative px-6 py-24 md:py-32 lg:py-40 flex flex-col items-center text-center overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-50 via-[#FAFAF8] to-[#FAFAF8] -z-10"></div>
          
          <div className="mb-6 inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
             <Zap className="mr-2 h-4 w-4" /> AI-Powered Document Search
          </div>

          <h2 className="max-w-4xl text-4xl font-extrabold tracking-tight text-stone-900 sm:text-5xl md:text-6xl lg:text-7xl">
            Understand Your Docs <span className="text-emerald-600">Instantly</span> with AI.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-stone-500 md:text-xl">
            Upload any document — PDFs, notes, research papers — and get instant AI-powered answers with exact page citations. No hallucinations, just facts.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Link href="/login">
              <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-white gap-2 font-semibold px-8 py-6 rounded-full text-lg shadow-lg shadow-emerald-200/50">
                Get Started Free <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
          </div>
          
          <div className="mt-8 flex items-center justify-center gap-6 text-sm text-stone-500">
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-600" /> Free to Use</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-600" /> No Credit Card Required</span>
          </div>
        </section>

        <section className="py-20 px-6 bg-white border-y border-stone-200">
          <div className="mx-auto max-w-6xl grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex flex-col items-center text-center p-8 rounded-2xl bg-white shadow-lg shadow-stone-200/60 border border-stone-100">
              <div className="p-4 rounded-full bg-emerald-50 text-emerald-600 mb-5">
                <Search className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold text-stone-900 mb-2">Smart Search</h3>
              <p className="text-stone-500">Instantly search through hundreds of pages to find exactly what you need.</p>
            </div>
            <div className="flex flex-col items-center text-center p-8 rounded-2xl bg-white shadow-lg shadow-stone-200/60 border border-stone-100">
              <div className="p-4 rounded-full bg-emerald-50 text-emerald-600 mb-5">
                <span className="text-3xl">🐼</span>
              </div>
              <h3 className="text-xl font-bold text-stone-900 mb-2">Zero Hallucinations</h3>
              <p className="text-stone-500">Every answer is strictly sourced from your actual documents — no made-up information, ever.</p>
            </div>
            <div className="flex flex-col items-center text-center p-8 rounded-2xl bg-white shadow-lg shadow-stone-200/60 border border-stone-100">
              <div className="p-4 rounded-full bg-emerald-50 text-emerald-600 mb-5">
                <FileText className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold text-stone-900 mb-2">Page-Level Citations</h3>
              <p className="text-stone-500">Every answer shows exactly which page and section it came from, so you can verify it yourself.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-stone-200 bg-[#FAFAF8] py-8 text-center text-stone-400">
        <p>© 2026 RFPanda Inc. All rights reserved.</p>
      </footer>
    </div>
  );
}
