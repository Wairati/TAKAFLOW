import { useEffect, useState } from "react";
import { createApiClient } from "@takaflow/api-client";

const api = createApiClient();

function App() {
  const [status, setStatus] = useState<"checking" | "ok" | "unreachable">("checking");

  useEffect(() => {
    api
      .health()
      .then(() => setStatus("ok"))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>TAKAFLOW — Admin Portal</h1>
      <p>Scaffold placeholder. Backend API status: <strong>{status}</strong></p>
    </main>
  );
}

export default App;
