"use client";

import { useMemo, useState } from "react";

export type LoginFormPayload = {
  identifier: string;
  password: string;
  remember: boolean;
};

type LoginFormProps = {
  endpoint?: string;
  onSuccess?: (payload: LoginFormPayload) => void;
};

export function LoginForm({ endpoint, onSuccess }: LoginFormProps) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resolvedEndpoint =
    endpoint ||
    process.env.NEXT_PUBLIC_AUTH_ENDPOINT ||
    "http://localhost:8000/api/auth/login";

  const formErrors = useMemo(() => {
    const errors: string[] = [];

    if (!identifier.trim()) {
      errors.push("User ID or Phone Number is required.");
    }

    if (!password) {
      errors.push("Password is required.");
    } else if (password.length < 8) {
      errors.push("Password must be at least 8 characters.");
    }

    return errors;
  }, [identifier, password]);

  const canSubmit = formErrors.length === 0 && !isSubmitting;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!canSubmit) {
      return;
    }

    // Backend expects 'identifier' not 'email'
    const payload = { identifier: identifier.trim(), password };

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
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Login failed. Try again.");
      }

      const data = await response.json();

      // Store auth token and user info in localStorage
      if (data.token) {
        localStorage.setItem("auth_token", data.token);
      }
      if (data.user?.user_id) {
        localStorage.setItem("user_id", data.user.user_id);
      }
      if (data.user?.name) {
        localStorage.setItem("user_name", data.user.name);
      }

      console.log(
        "✅ Login successful, stored auth token and user_id:",
        data.user?.user_id,
      );

      // Redirect to home page
      window.location.href = "/";

      onSuccess?.({ identifier: identifier.trim(), password, remember });
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
            htmlFor="identifier"
            className="text-sm font-medium text-zinc-700 dark:text-zinc-200"
          >
            User ID or Phone Number
          </label>
          <input
            id="identifier"
            name="identifier"
            type="text"
            autoComplete="username"
            required
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            className="w-full rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100 shadow-sm focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 dark:focus:ring-emerald-500/30"
            placeholder="user_001 or +91-90000-00001"
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
        className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-300 dark:disabled:bg-zinc-700"
      >
        {isSubmitting ? "Signing in..." : "Sign in"}
      </button>

      {/* Test credentials hint */}
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50 px-4 py-3 text-xs text-zinc-600 dark:text-zinc-400">
        <p className="font-medium mb-1">Test Credentials:</p>
        <p>
          User ID:{" "}
          <code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">
            user_001
          </code>
        </p>
        <p>
          Password:{" "}
          <code className="bg-zinc-200 dark:bg-zinc-700 px-1 rounded">
            Password@123
          </code>
        </p>
      </div>
    </form>
  );
}
