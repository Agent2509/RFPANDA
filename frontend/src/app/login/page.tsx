// ============================================================================
// ApexTender v2.0 — Login Page
// ============================================================================

'use client';

import { AuthForm } from '@/components/auth/AuthForm';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.15),rgba(255,255,255,0))]">
      <AuthForm mode="login" />
    </div>
  );
}
