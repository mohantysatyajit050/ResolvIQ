import { useEffect, useState } from "react";
import { apiClient } from "./api/client";

type ReadyResponse = {
  status: string;
  checks: Record<string, string>;
};

function App() {
  const [api, setApi] = useState<"loading" | "ok" | "down">("loading");
  const [ready, setReady] = useState<ReadyResponse | null>(null);

  useEffect(() => {
    apiClient
      .get("/health")
      .then(() => setApi("ok"))
      .catch(() => setApi("down"));

    apiClient
      .get<ReadyResponse>("/health/ready", { validateStatus: () => true })
      .then((res) => setReady(res.data))
      .catch(() => setReady(null));
  }, []);

  const apiText =
    api === "loading" ? "checking..." : api === "ok" ? "running" : "NOT reachable";

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1>ResolvIQ</h1>
      <p>API: {apiText}</p>
      {ready && (
        <ul>
          {Object.entries(ready.checks).map(([name, value]) => (
            <li key={name}>
              {name}: {value}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;
