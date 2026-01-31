"use client";

import { useMutation } from "@tanstack/react-query";
import { API_CONFIG } from "@/utils/config";

export type LoginPayload = {
  identifier: string;
  password: string;
};

export type LoginSuccess = {
  token: string;
  user?: { user_id: string; name?: string };
};

async function loginFn(payload: LoginPayload): Promise<LoginSuccess> {
  const url = API_CONFIG.getApiUrl("auth/login");
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      typeof data.detail === "string" ? data.detail : "Login failed. Try again."
    );
  }
  return data as LoginSuccess;
}

export function useLogin(options?: {
  onSuccess?: (data: LoginSuccess, payload: LoginPayload) => void;
  onError?: (error: Error) => void;
}) {
  return useMutation({
    mutationFn: loginFn,
    onSuccess(data, variables) {
      if (data.token) localStorage.setItem("auth_token", data.token);
      if (data.user?.user_id)
        localStorage.setItem("user_id", data.user.user_id);
      if (data.user?.name) localStorage.setItem("user_name", data.user.name);
      options?.onSuccess?.(data, variables);
    },
    onError: options?.onError,
  });
}
