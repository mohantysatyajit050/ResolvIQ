import { useAuth } from "../../hooks/useAuth";

export default function MyOrdersPage() {
  const { user } = useAuth();
  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900">My orders</h1>
      <p className="mt-2 text-slate-600">
        Hello {user?.name}. The order list and the complaint form come on Day 9.
      </p>
    </section>
  );
}
