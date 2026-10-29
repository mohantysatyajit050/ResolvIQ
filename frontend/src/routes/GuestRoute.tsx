import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { homePathFor } from "../lib/constants";

type LocationState = { from?: { pathname?: string } } | null;

/** For the login and register pages: people who are already logged in are sent away. */
export default function GuestRoute() {
  const { user, status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <p className="p-6 text-slate-600">Loading...</p>;
  }
  if (user) {
    const from = (location.state as LocationState)?.from?.pathname;
    return <Navigate to={from ?? homePathFor(user.role)} replace />;
  }
  return <Outlet />;
}
