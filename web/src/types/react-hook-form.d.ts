/**
 * react-hook-form published types reference ../src/* which is not in the package.
 * This declaration provides useForm and related types so our auth forms type-check.
 */
declare module "react-hook-form" {
  import type * as React from "react"

  export type FieldValues = Record<string, unknown>
  export type FieldError = { message?: string; type?: string }
  export type FieldErrors<T extends FieldValues = FieldValues> = Partial<Record<string, FieldError>>
  export type FieldPath<T extends FieldValues> = string & keyof T
  export type DefaultValues<T extends FieldValues> = DeepPartial<T>
  type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] }
  export type Resolver<T extends FieldValues> = (
    values: T
  ) => Promise<{ values: T; errors: FieldErrors<T> }> | { values: T; errors: FieldErrors<T> }
  export type Control<T extends FieldValues = FieldValues> = unknown
  export type FormState<T extends FieldValues = FieldValues> = { errors: FieldErrors<T> }
  export type UseFormHandleSubmit<T extends FieldValues = FieldValues> = (
    callback: (data: T) => void | Promise<void>
  ) => (e?: React.BaseSyntheticEvent) => Promise<void>
  export type UseFormReturn<T extends FieldValues = FieldValues> = {
    control: Control<T>
    handleSubmit: UseFormHandleSubmit<T>
    formState: FormState<T>
    getFieldState: (name: FieldPath<T>, formState: FormState<T>) => { invalid: boolean; isTouched: boolean; isDirty: boolean; error?: FieldError }
  }
  export type UseFormProps<T extends FieldValues = FieldValues> = {
    resolver?: Resolver<T>
    defaultValues?: DefaultValues<T>
  }

  export function useForm<T extends FieldValues = FieldValues>(
    props?: UseFormProps<T>
  ): UseFormReturn<T>

  export type ControllerRenderProps<TFieldValues extends FieldValues = FieldValues, TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>> = {
    field: { value: string | number | readonly string[]; onChange: (e: React.ChangeEvent<HTMLInputElement> | unknown) => void; onBlur: () => void; ref: React.RefCallback<HTMLInputElement>; name: TName }
    fieldState: { invalid: boolean; isTouched: boolean; isDirty: boolean; error?: FieldError }
    formState: FormState<TFieldValues>
  }
  export type ControllerProps<TFieldValues extends FieldValues = FieldValues, TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>> = {
    name: TName
    control?: Control<TFieldValues>
    render: (props: ControllerRenderProps<TFieldValues, TName>) => React.ReactElement
  }
  export const FormProvider: React.ComponentType<{ children: React.ReactNode }>
  export function Controller<TFieldValues extends FieldValues = FieldValues, TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>>(
    props: ControllerProps<TFieldValues, TName>
  ): React.ReactElement
  export function useFormContext<T extends FieldValues = FieldValues>(): UseFormReturn<T>
  export function useFormState<T extends FieldValues = FieldValues>(props?: { control?: Control<T>; name?: FieldPath<T> }): FormState<T>
}
