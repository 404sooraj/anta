"use client"

import { useMutation } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { loginWithCredentials, signUp } from "@/lib/api/auth"
import type { LoginInput, SignUpInput } from "@/lib/validations/auth"

export function useLoginMutation() {
  const router = useRouter()

  return useMutation({
    mutationFn: loginWithCredentials,
    onSuccess: () => {
      toast.success("Login successful")
      router.push("/")
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Login failed")
    },
  })
}

export function useSignUpMutation() {
  const router = useRouter()

  return useMutation({
    mutationFn: signUp,
    onSuccess: () => {
      toast.success("Account created")
      router.push("/")
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Sign up failed")
    },
  })
}
