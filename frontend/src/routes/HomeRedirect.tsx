import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { homePathFor } from "../lib/constants";

export default function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? homePathFor(user.role) : "/login"} replace />;
}
