"use client";

import { useLogin } from "@/lib/auth/useLogin";
import { useMemo, useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

export type LoginFormPayload = {
  identifier: string;
  password: string;
  remember: boolean;
};

type LoginFormProps = {
  onSuccess?: (payload: LoginFormPayload) => void;
};

const inputBase =
  "w-full rounded-lg border border-zinc-700 bg-zinc-800/50 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 transition focus:outline-none focus:ring-2 focus:ring-[#B19EEF]/50 focus:border-[#B19EEF]/50";

const ACCENT = "#B19EEF";

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);

  const login = useLogin({
    onSuccess() {
      toast.success("Signed in successfully");
      window.location.href = "/";
    },
    onError(err) {
      toast.error(err.message);
    },
  });
  const isSubmitting = login.isPending;

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

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canSubmit) {
      if (formErrors.length > 0) {
        formErrors.forEach((msg) => toast.error(msg));
      }
      return;
    }

    login.mutate(
      { identifier: identifier.trim(), password },
      {
        onSuccess() {
          onSuccess?.({ identifier: identifier.trim(), password, remember });
        },
      }
    );
  };

  return (
    <div className="space-y-6">
      {/* Social login */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-4">
          <div className="space-y-2">
            {/* <label
              htmlFor="identifier"
              className="text-sm font-medium text-zinc-300"
            >
              User ID or Phone Number
            </label> */}
            <input
              id="identifier"
              name="identifier"
              type="text"
              autoComplete="username"
              required
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              className={inputBase}
              placeholder="user_001 or +91-90000-00001"
            />
          </div>

          <div className="space-y-2">
            {/* <label
              htmlFor="password"
              className="text-sm font-medium text-zinc-300"
            >
              Password
            </label> */}
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={`${inputBase} pr-11`}
                placeholder="Enter your password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-zinc-400 transition hover:bg-zinc-700/50 hover:text-zinc-200"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold text-white shadow-lg transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-[#B19EEF] focus:ring-offset-2 focus:ring-offset-zinc-950 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          style={{ backgroundColor: ACCENT }}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Signing in...
            </>
          ) : (
            "Continue"
          )}
        </button>
      </form>


    </div>
  );
}
