"use client";

import { useEffect, useState } from "react";
import api from "@/utils/api";

type RequireAuthProps = {
  children: React.ReactNode;
};

/**
 * Protects routes by ensuring the user is authenticated.
 * - If no auth_token in localStorage, redirects to /login.
 * - Calls GET /me to validate the token; api interceptor redirects to /login on 401/403.
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const token = localStorage.getItem("auth_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    api
      .get("/me")
      .then(() => {
        setIsChecking(false);
      })
      .catch(() => {
        // Interceptor handles redirect on 401/403; just stop loading
        setIsChecking(false);
      });
  }, []);

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-zinc-50 to-white dark:from-zinc-950 dark:to-zinc-900">
        <div className="text-sm text-zinc-500 dark:text-zinc-400">
          Checking authentication…
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
