import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { homePathFor } from "../lib/constants";

export default function ForbiddenPage() {
  const { user, logout } = useAuth();
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-4xl font-bold text-slate-300">403</p>
        <h1 className="mt-2 text-xl font-semibold text-slate-900">
          You do not have access to this page
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          This page is hidden to keep the app tidy. The real protection is on the
          server, which checks every request.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            to={user ? homePathFor(user.role) : "/login"}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Go to my page
          </Link>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            Log out
          </button>
        </div>
      </div>
    </main>
  );
}
