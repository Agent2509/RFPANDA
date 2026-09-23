// ============================================================================
// RFPANDA — Auth form (sign in / sign up)
// ============================================================================

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui';
import { Mail, Lock, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';
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
          setSuccessMessage('Account created! You can now sign in.');
          setTimeout(() => router.push('/login'), 1500);
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md animate-fade-up">
      {/* Brand + heading */}
      <div className="mb-7 flex flex-col items-center text-center">
        <Link href="/" className="grid h-12 w-12 place-items-center rounded-2xl bg-zinc-900 text-xl shadow-card">
          🐼
        </Link>
        <h1 className="mt-4 text-2xl font-extrabold tracking-tight text-zinc-900">
          {mode === 'login' ? 'Welcome back' : 'Create your account'}
        </h1>
        <p className="mt-1 text-sm text-zinc-500">
          {mode === 'login'
            ? 'Sign in to your RFPANDA workspace'
            : 'Start turning documents into answers'}
        </p>
      </div>

      <div className="panel p-6 sm:p-7">
        {errorMessage && (
          <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-200/70 bg-rose-50 p-3 text-sm text-rose-700 animate-fade-in">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-emerald-200/70 bg-emerald-50 p-3 text-sm text-emerald-700 animate-fade-in">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-zinc-600">Email</label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="field field-icon"
              />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold text-zinc-600">Password</label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="field field-icon"
              />
            </div>
          </div>

          {mode === 'signup' && (
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-zinc-600">Confirm password</label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="field field-icon"
                />
              </div>
            </div>
          )}

          <Button type="submit" isLoading={isSubmitting} className="mt-1 w-full gap-2 py-2.5">
            {mode === 'login' ? 'Sign in' : 'Create account'}
            {!isSubmitting && <ArrowRight className="h-4 w-4" />}
          </Button>
        </form>

        <div className="mt-6 border-t border-zinc-100 pt-5 text-center text-sm text-zinc-500">
          {mode === 'login' ? (
            <>
              Don’t have an account?{' '}
              <Link href="/signup" className="font-semibold text-brand-600 hover:text-brand-700">
                Sign up
              </Link>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <Link href="/login" className="font-semibold text-brand-600 hover:text-brand-700">
                Sign in
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
