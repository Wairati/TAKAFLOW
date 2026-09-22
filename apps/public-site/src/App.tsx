// Phase 12 (§05, §22 nice-to-have): a minimal public site reading real
// collection-point and material data from the API. No authentication, no
// login state at all — this is the one app that's genuinely just a
// read-only window into what the branches accept and pay.
import { useEffect, useState } from "react";
import { createApiClient } from "@takaflow/api-client";
import type { AcceptedMaterialOut, CollectionPointOut } from "@takaflow/types";

const api = createApiClient();

function BranchCard({ point }: { point: CollectionPointOut }) {
  const [materials, setMaterials] = useState<AcceptedMaterialOut[] | null>(null);

  useEffect(() => {
    api
      .listPublicAcceptedMaterials(point.id)
      .then(setMaterials)
      .catch(() => setMaterials([]));
  }, [point.id]);

  return (
    <article style={{ border: "1px solid #ddd", borderRadius: 8, padding: "1.2rem", marginBottom: "1rem" }}>
      <h3 style={{ margin: "0 0 0.3rem" }}>{point.name}</h3>
      <p style={{ margin: "0 0 0.6rem", color: "#555" }}>
        {point.address}, {point.county}
        {point.opening_hours ? ` — ${point.opening_hours}` : ""}
      </p>
      {materials === null ? (
        <p style={{ color: "#888" }}>Loading accepted materials…</p>
      ) : materials.length === 0 ? (
        <p style={{ color: "#888" }}>No materials currently listed for this branch.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.92rem" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>
              <th>Material</th>
              <th>We pay</th>
            </tr>
          </thead>
          <tbody>
            {materials.map((m) => (
              <tr key={m.material.id}>
                <td>{m.material.name}</td>
                <td>
                  {m.current_rate.rate} / {m.material.unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </article>
  );
}

function App() {
  const [points, setPoints] = useState<CollectionPointOut[] | null>(null);

  useEffect(() => {
    api
      .listPublicCollectionPoints()
      .then(setPoints)
      .catch(() => setPoints([]));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 720, margin: "0 auto", padding: "2rem 1rem" }}>
      <header style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
        <img src="/logo.jpeg" alt="TAKAFLOW logo" style={{ width: 48, height: 48, objectFit: "contain" }} />
        <div>
          <h1 style={{ margin: 0, fontSize: "1.6rem" }}>TAKAFLOW</h1>
          <p style={{ margin: 0, color: "#666", fontStyle: "italic" }}>Turning Waste Into Worth</p>
        </div>
      </header>

      <p style={{ lineHeight: 1.5, color: "#333" }}>
        Bring your recyclable materials to any branch below and get paid on the spot — no registration
        needed. Rates and accepted materials are shown live for each branch.
      </p>

      <h2 style={{ fontSize: "1.2rem", marginTop: "2rem" }}>Our collection points</h2>
      {points === null ? (
        <p>Loading branches…</p>
      ) : points.length === 0 ? (
        <p>No branches are currently listed.</p>
      ) : (
        points.map((point) => <BranchCard key={point.id} point={point} />)
      )}
    </main>
  );
}

export default App;
