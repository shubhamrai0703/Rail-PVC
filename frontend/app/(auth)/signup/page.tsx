"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/Button";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    const supabase = createClient();
    const { error: authError } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    setDone(true);
  }

  if (done) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl px-8 py-7 shadow-sm text-center">
        <div className="text-[32px] mb-3">✉️</div>
        <h2 className="text-[17px] font-semibold text-slate-900 mb-2">Check your email</h2>
        <p className="text-[13px] text-slate-500">
          We sent a confirmation link to{" "}
          <span className="font-medium text-slate-700">{email}</span>.
          <br />
          Click it to activate your account.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl px-8 py-7 shadow-sm">
      <h2 className="text-[17px] font-semibold text-slate-900 mb-1">Create account</h2>
      <p className="text-[13px] text-slate-500 mb-6">
        Your team admin may have sent you an invite — check your inbox first.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="email"
            className="block text-[12px] font-medium text-slate-700 mb-1.5"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full h-9 px-3 text-[13px] text-slate-900 bg-white border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-400 transition-colors"
            placeholder="you@railway.gov.in"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-[12px] font-medium text-slate-700 mb-1.5"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full h-9 px-3 text-[13px] text-slate-900 bg-white border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-400 transition-colors"
            placeholder="Min. 8 characters"
          />
        </div>

        <div>
          <label
            htmlFor="confirm"
            className="block text-[12px] font-medium text-slate-700 mb-1.5"
          >
            Confirm password
          </label>
          <input
            id="confirm"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full h-9 px-3 text-[13px] text-slate-900 bg-white border border-slate-200 rounded-lg outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-400 transition-colors"
            placeholder="••••••••"
          />
        </div>

        {error && (
          <p className="text-[12px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" className="w-full" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </Button>
      </form>

      <p className="text-[12px] text-slate-500 text-center mt-5">
        Already have an account?{" "}
        <Link href="/login" className="text-slate-900 font-medium hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
