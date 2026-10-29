import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { homePathFor } from "../../lib/constants";

export default function AppShell() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link
            to={homePathFor(user.role)}
            className="text-lg font-semibold text-indigo-600"
          >
            ResolvIQ
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-700">{user.name}</span>
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              {user.role}
            </span>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-slate-300 px-3 py-1 text-slate-700 hover:bg-slate-100"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl p-4">
        <Outlet />
      </main>
    </div>
  );
}
