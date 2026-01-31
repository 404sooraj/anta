"use client";

import { useMemo, useState } from "react";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type LoginFormPayload = {
  email: string;
  password: string;
  remember: boolean;
};

type LoginFormProps = {
  endpoint?: string;
  onSuccess?: (payload: LoginFormPayload) => void;
};

export function LoginForm({ endpoint, onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resolvedEndpoint =
    endpoint || process.env.NEXT_PUBLIC_AUTH_ENDPOINT || "/api/auth/login";

  const formErrors = useMemo(() => {
    const errors: string[] = [];

    if (!email.trim()) {
      errors.push("Email is required.");
    } else if (!EMAIL_REGEX.test(email)) {
      errors.push("Enter a valid email address.");
    }

    if (!password) {
      errors.push("Password is required.");
    } else if (password.length < 8) {
      errors.push("Password must be at least 8 characters.");
    }

    return errors;
  }, [email, password]);

  const canSubmit = formErrors.length === 0 && !isSubmitting;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!canSubmit) {
      return;
    }

    const payload = { email: email.trim(), password, remember };

    try {
      setIsSubmitting(true);
      const response = await fetch(resolvedEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Login failed. Try again.");
      }

      onSuccess?.(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <label
            htmlFor="email"
            className="text-sm font-medium text-zinc-700 dark:text-zinc-200"
          >
            Work email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100 shadow-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 dark:focus:ring-emerald-500/30"
            placeholder="you@company.com"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="password"
            className="text-sm font-medium text-zinc-700 dark:text-zinc-200"
          >
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3 pr-12 text-sm text-zinc-900 dark:text-zinc-100 shadow-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 dark:focus:ring-emerald-500/30"
              placeholder="Enter your password"
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-zinc-500 hover:text-emerald-600"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center gap-2 text-zinc-600 dark:text-zinc-400">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500"
            />
            Remember me
          </label>
          <a
            href="/forgot-password"
            className="text-xs font-medium text-emerald-600 hover:text-emerald-700 dark:text-emerald-400"
          >
            Forgot password?
          </a>
        </div>
      </div>

      {formErrors.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-700">
          <ul className="list-disc space-y-1 pl-4">
            {formErrors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
      >
        {isSubmitting ? "Signing in..." : "Sign in"}
      </button>


      <p className="text-xs text-zinc-500">
        Need an account?{" "}
        <a
          href="/signup"
          className="font-medium text-emerald-600 hover:text-emerald-700"
        >
          Create one
        </a>
      </p>

      <p className="text-[11px] text-zinc-400">
        This login form is ready for backend integration at{" "}
        <span className="font-mono text-emerald-600">{resolvedEndpoint}</span>.
      </p>
    </form>
  );
}
