// ============================================================================
// ApexTender v2.0 — Supabase Authentication Form Component
// Handles sign in, sign up, session persistence, and error feedback.
// ============================================================================

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui';
import { Mail, Lock, AlertCircle, CheckCircle2, ShieldCheck, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface AuthFormProps {
  mode: 'login' | 'signup';
}

export function AuthForm({ mode }: AuthFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { signIn, signUp } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!email || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    if (mode === 'signup' && password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters.');
      return;
    }

    setIsSubmitting(true);

    try {
      if (mode === 'login') {
        await signIn(email, password);
        router.push('/dashboard');
      } else {
        const data = await signUp(email, password);
        if (data.session) {
          router.push('/dashboard');
        } else {
          setSuccessMessage('Registration successful! You may now sign in.');
          setTimeout(() => {
            router.push('/login');
          }, 1500);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 bg-white/90 border border-stone-200 rounded-2xl shadow-2xl backdrop-blur-xl">
      {/* Brand Header */}
      <div className="flex flex-col items-center text-center mb-8">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-600 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 mb-3">
          <ShieldCheck className="w-7 h-7 text-slate-950 font-bold" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-stone-900">
          {mode === 'login' ? 'Welcome to ApexTender' : 'Create an Account'}
        </h1>
        <p className="text-sm text-stone-500 mt-1">
          {mode === 'login'
            ? 'Sign in to access your enterprise RFP workspace'
            : 'Get started with high-precision RAG RFP analysis'}
        </p>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200/60 text-rose-700 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Success Alert */}
      {successMessage && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200/60 text-emerald-700 text-sm flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600 mt-0.5" />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-stone-600 uppercase tracking-wider mb-2">
            Work Email
          </label>
          <div className="relative">
            <Mail className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@enterprise.com"
              required
              className="w-full pl-11 pr-4 py-2.5 bg-stone-100/80 border border-stone-300 rounded-xl text-stone-800 placeholder-stone-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-stone-600 uppercase tracking-wider mb-2">
            Password
          </label>
          <div className="relative">
            <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="w-full pl-11 pr-4 py-2.5 bg-stone-100/80 border border-stone-300 rounded-xl text-stone-800 placeholder-stone-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        {mode === 'signup' && (
          <div>
            <label className="block text-xs font-semibold text-stone-600 uppercase tracking-wider mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full pl-11 pr-4 py-2.5 bg-stone-100/80 border border-stone-300 rounded-xl text-stone-800 placeholder-stone-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
              />
            </div>
          </div>
        )}

        <Button
          type="submit"
          isLoading={isSubmitting}
          className="w-full mt-2 py-3 rounded-xl font-semibold flex items-center justify-center gap-2"
        >
          {mode === 'login' ? 'Sign In to Workspace' : 'Create Free Account'}
          <ArrowRight className="w-4 h-4" />
        </Button>
      </form>

      <div className="mt-8 pt-6 border-t border-stone-200/80 text-center text-sm text-stone-500">
        {mode === 'login' ? (
          <p>
            Don't have an account?{' '}
            <Link href="/signup" className="text-emerald-600 hover:text-emerald-700 font-semibold underline underline-offset-4">
              Sign up
            </Link>
          </p>
        ) : (
          <p>
            Already have an account?{' '}
            <Link href="/login" className="text-emerald-600 hover:text-emerald-700 font-semibold underline underline-offset-4">
              Sign in
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
