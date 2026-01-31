import type { LoginInput, SignUpInput } from "@/lib/validations/auth"

const MOCK_DELAY_MS = 800

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function loginWithCredentials(
  data: LoginInput
): Promise<{ user: { email: string } }> {
  await delay(MOCK_DELAY_MS)
  return { user: { email: data.email } }
}

export async function signUp(
  data: SignUpInput
): Promise<{ user: { email: string; name?: string } }> {
  await delay(MOCK_DELAY_MS)
  return {
    user: {
      email: data.email,
      ...(data.name ? { name: data.name } : {}),
    },
  }
}
