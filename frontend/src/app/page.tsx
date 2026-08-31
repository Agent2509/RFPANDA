'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui';
import { Shield, Zap, Search, ArrowRight, FileText, CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-200">
      <header className="flex h-16 items-center justify-between border-b border-emerald-900/30 bg-slate-900/50 px-6 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-emerald-500" />
          <h1 className="text-xl font-bold tracking-tight text-emerald-50">
            RFP<span className="text-emerald-500">ANDA</span>
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="outline" className="text-emerald-400 border-emerald-900/50 hover:bg-emerald-900/20">
              Sign In / Enter App
            </Button>
          </Link>
        </div>
      </header>

      <main className="flex-1">
        <section className="relative px-6 py-24 md:py-32 lg:py-40 flex flex-col items-center text-center overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-900/20 via-slate-950 to-slate-950 -z-10"></div>
          
          <div className="mb-6 inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm font-medium text-emerald-400 backdrop-blur-sm">
             <Zap className="mr-2 h-4 w-4" /> v2.0 Production Grade RAG
          </div>

          <h2 className="max-w-4xl text-4xl font-extrabold tracking-tight text-white sm:text-5xl md:text-6xl lg:text-7xl">
            Analyze RFPs <span className="text-emerald-500">10x Faster</span> with AI.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-400 md:text-xl">
            Upload massive Request for Proposal (RFP) documents and instantly extract insights, SLAs, and technical requirements with zero hallucinations. Built for enterprise sales teams.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Link href="/login">
              <Button size="lg" className="bg-emerald-600 hover:bg-emerald-500 text-white gap-2 font-semibold px-8 py-6 rounded-full text-lg shadow-[0_0_40px_-10px_#059669]">
                Get Started Free <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
          </div>
          
          <div className="mt-8 flex items-center justify-center gap-6 text-sm text-slate-500">
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-500" /> Free Tier: 3 PDFs / month</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="h-4 w-4 text-emerald-500" /> No Credit Card Required</span>
          </div>
        </section>

        <section className="py-20 px-6 bg-slate-900/30 border-y border-emerald-900/20">
          <div className="mx-auto max-w-6xl grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
              <div className="p-3 rounded-full bg-emerald-900/30 text-emerald-400 mb-4">
                <Search className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Vector-Powered RAG</h3>
              <p className="text-slate-400">Instantly search thousands of pages using Voyage AI dense embeddings and hybrid retrieval.</p>
            </div>
            <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
              <div className="p-3 rounded-full bg-emerald-900/30 text-emerald-400 mb-4">
                <Shield className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Zero Hallucinations</h3>
              <p className="text-slate-400">Our ultra-strict Llama-3 AI guarantees answers are strictly sourced from your uploaded documents, preventing liability.</p>
            </div>
            <div className="flex flex-col items-center text-center p-6 rounded-2xl bg-slate-900/50 border border-slate-800">
              <div className="p-3 rounded-full bg-emerald-900/30 text-emerald-400 mb-4">
                <FileText className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Page-Level Citations</h3>
              <p className="text-slate-400">Every claim is backed by exact source references and bounding-box page citations for human review.</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-emerald-900/30 py-8 text-center text-slate-500">
        <p>© 2026 RFPanda Inc. All rights reserved.</p>
      </footer>
    </div>
  );
}
