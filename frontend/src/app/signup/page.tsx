// ============================================================================
// ApexTender v2.0 — Signup Page
// ============================================================================

'use client';

import { AuthForm } from '@/components/auth/AuthForm';

export default function SignupPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#FAFAF8] font-sans">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl shadow-stone-200/60 p-8 border border-stone-100">
        <AuthForm mode="signup" />
      </div>
    </div>
  );
}
