import { createBrowserRouter } from "react-router-dom";
import AppShell from "../components/layout/AppShell";
import AgentQueuePage from "../pages/agent/AgentQueuePage";
import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import MyOrdersPage from "../pages/customer/MyOrdersPage";
import MyTicketsPage from "../pages/customer/MyTicketsPage";
import NewComplaintPage from "../pages/customer/NewComplaintPage";
import TicketDetailPage from "../pages/customer/TicketDetailPage";
import NotFoundPage from "../pages/NotFoundPage";
import GuestRoute from "./GuestRoute";
import HomeRedirect from "./HomeRedirect";
import ProtectedRoute from "./ProtectedRoute";

export const router = createBrowserRouter([
  {
    // only for people who are NOT logged in
    element: <GuestRoute />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    // any logged-in user: send them to the right home page
    element: <ProtectedRoute />,
    children: [{ path: "/", element: <HomeRedirect /> }],
  },
  {
    element: <ProtectedRoute allowedRoles={["customer"]} />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/orders", element: <MyOrdersPage /> },
          { path: "/tickets", element: <MyTicketsPage /> },
          { path: "/tickets/new", element: <NewComplaintPage /> },
          { path: "/tickets/:ticketId", element: <TicketDetailPage /> },
        ],
      },
    ],
  },
  {
    element: <ProtectedRoute allowedRoles={["agent", "admin"]} />,
    children: [
      {
        element: <AppShell />,
        children: [{ path: "/agent/queue", element: <AgentQueuePage /> }],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
