// ============================================================================
// RFPANDA — UI Primitives
// A small, dependency-free component kit used across the app.
// ============================================================================

import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/* ------------------------------------------------------------------ Button */

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, disabled, children, ...props }, ref) => {
    const base =
      'inline-flex items-center justify-center font-semibold whitespace-nowrap rounded-xl transition-all ' +
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 focus-visible:ring-offset-1 ' +
      'disabled:opacity-50 disabled:pointer-events-none active:scale-[0.985]';

    const variants = {
      primary: 'bg-brand-600 text-white shadow-sm hover:bg-brand-700 hover:shadow-md',
      secondary: 'bg-zinc-900 text-white shadow-sm hover:bg-zinc-800',
      outline: 'border border-zinc-200 bg-white text-zinc-700 shadow-sm hover:bg-zinc-50 hover:border-zinc-300',
      danger: 'bg-rose-600 text-white shadow-sm hover:bg-rose-700',
      ghost: 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900',
    };

    const sizes = {
      sm: 'text-xs px-2.5 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-5 py-2.5 gap-2.5',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(base, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Spinner className="h-3.5 w-3.5" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

/* ----------------------------------------------------------------- Spinner */

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cn('animate-spin text-current', className)} fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

/* ------------------------------------------------------------------- Badge */

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'purple';
}

export function Badge({ className, variant = 'default', children, ...props }: BadgeProps) {
  const variants = {
    default: 'bg-zinc-100 text-zinc-600 border-zinc-200',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200/70',
    warning: 'bg-amber-50 text-amber-700 border-amber-200/70',
    error: 'bg-rose-50 text-rose-700 border-rose-200/70',
    info: 'bg-sky-50 text-sky-700 border-sky-200/70',
    purple: 'bg-brand-50 text-brand-700 border-brand-200/70',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

/* -------------------------------------------------------------------- Card */

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('panel', className)} {...props} />;
}

/* ---------------------------------------------------------------- Progress */

export function ProgressBar({
  value,
  className,
  barClassName,
}: {
  value: number;
  className?: string;
  barClassName?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className={cn('w-full overflow-hidden rounded-full bg-zinc-100', className)}>
      <div
        className={cn('h-full rounded-full bg-brand-600 transition-all duration-300 ease-out', barClassName)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
