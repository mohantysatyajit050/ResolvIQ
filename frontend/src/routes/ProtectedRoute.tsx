import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import ForbiddenPage from "../pages/ForbiddenPage";
import type { UserRole } from "../types/auth";

type ProtectedRouteProps = {
  /** If set, only these roles may open the page. */
  allowedRoles?: UserRole[];
};

/**
 * This only improves the experience. It is NOT security:
 * the server checks every request again, whatever this screen shows.
 */
export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <p className="p-6 text-slate-600">Loading...</p>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <ForbiddenPage />;
  }
  return <Outlet />;
}
