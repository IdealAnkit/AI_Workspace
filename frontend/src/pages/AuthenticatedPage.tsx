import { useAuthStore } from '@/store/authStore'

/** A deliberately minimal authenticated landing state; no workspace/dashboard is built in this phase. */
function AuthenticatedPage() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-center">
      <section className="max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-8">
        <p className="text-sm font-medium text-cyan-400">Authenticated</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Hello, {user?.full_name}</h1>
        <p className="mt-3 text-slate-400">
          Your authentication foundation is ready. Workspace features arrive in later phases.
        </p>
        <button
          className="mt-6 rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500"
          onClick={() => void logout()}
          type="button"
        >
          Sign out
        </button>
      </section>
    </main>
  )
}

export default AuthenticatedPage
