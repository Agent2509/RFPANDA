import { AuthForm } from '@/components/auth/AuthForm';

export default function LoginPage() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas p-5">
      <div className="pointer-events-none absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
      <div className="pointer-events-none absolute -top-32 left-1/2 h-80 w-[36rem] -translate-x-1/2 rounded-full bg-brand-300/25 blur-3xl" />
      <div className="relative">
        <AuthForm mode="login" />
      </div>
    </div>
  );
}
