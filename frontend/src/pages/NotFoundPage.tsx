import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6 text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-indigo-600">
        Error 404
      </p>
      <h1 className="mt-3 text-3xl font-bold text-slate-900">
        Page not found
      </h1>
      <p className="mt-2 text-slate-600">
        The page you are looking for doesn't exist.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-lg bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-700"
      >
        Back to home
      </Link>
    </main>
  );
}
