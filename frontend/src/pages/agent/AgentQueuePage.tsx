import { useAuth } from "../../hooks/useAuth";

export default function AgentQueuePage() {
  const { user } = useAuth();
  return (
    <section>
      <h1 className="text-xl font-semibold text-slate-900">Agent queue</h1>
      <p className="mt-2 text-slate-600">
        Hello {user?.name}. The ticket queue comes on Day 10.
      </p>
    </section>
  );
}
