import { z } from "zod"

const passwordSchema = z.string().min(8, "Password must be at least 8 characters")

export const loginSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  password: passwordSchema,
})

export const signUpSchema = z
  .object({
    name: z.string().min(1, "Name is required").optional(),
    email: z.string().email("Please enter a valid email"),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  })

export type LoginInput = z.infer<typeof loginSchema>
export type SignUpInput = z.infer<typeof signUpSchema>
