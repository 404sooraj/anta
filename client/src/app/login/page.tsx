import { LoginFooter } from "@/components/auth/LoginFooter";
import { LoginForm } from "@/components/auth/LoginForm";
import { LoginHeader } from "@/components/auth/LoginHeader";
import { LoginSidePanel } from "@/components/auth/LoginSidePanel";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-linear-to-b from-zinc-50 via-white to-zinc-100 dark:from-zinc-950 dark:via-zinc-950 dark:to-zinc-900">
      <div className="mx-auto flex min-h-screen h-full w-full flex-col gap-8 px-6 py-12 lg:flex-row lg:items-center">
        <div className="w-full lg:w-5/12">
          <LoginSidePanel />
        </div>

        <div className="w-full lg:w-7/12">
          <div className="rounded-3xl border border-zinc-200 bg-white/90 p-8 shadow-xl shadow-zinc-200/40 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/90 dark:shadow-none">
            <div className="space-y-6">
              <LoginHeader />
              <div>
                <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
                  Welcome back
                </h1>
                <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
                  Sign in to continue managing the Antaryami voice assistant.
                </p>
              </div>
              <LoginForm />
            </div>
            <LoginFooter />
          </div>
        </div>
      </div>
    </div>
  );
}
