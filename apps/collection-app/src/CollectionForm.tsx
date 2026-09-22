// Recording a walk-in collection (§25 item 7: no supplier registration —
// collector name/phone are optional, free-text, never deduplicated).
// The material dropdown reads from the on-device reference cache, not a
// live API call, so this form works fully offline once materials have
// been fetched at least once (§10).
import { useEffect, useState, type FormEvent } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "./db";
import { queueCollection } from "./sync";
import { api } from "./auth";
import type { UserOut } from "@takaflow/types";

export function CollectionForm({ user }: { user: UserOut }) {
  const cache = useLiveQuery(() => db.referenceCache.get("accepted_materials"), []);
  const [materialId, setMaterialId] = useState<number | "">("");
  const [quantity, setQuantity] = useState("");
  const [grade, setGrade] = useState("");
  const [collectorName, setCollectorName] = useState("");
  const [collectorPhone, setCollectorPhone] = useState("");
  const [justQueued, setJustQueued] = useState(false);

  // Refresh the reference cache opportunistically whenever online - never
  // blocks the form, and a stale cache still lets the form work offline.
  useEffect(() => {
    if (!user.collection_point_id || !navigator.onLine) return;
    api
      .listAcceptedMaterials(user.collection_point_id)
      .then((materials) =>
        db.referenceCache.put({
          id: "accepted_materials",
          collection_point_id: user.collection_point_id!,
          materials,
          fetched_at: new Date().toISOString(),
        })
      )
      .catch(() => {
        // Offline or the request failed - the existing cache (if any) still stands.
      });
  }, [user.collection_point_id]);

  const materials = cache?.materials ?? [];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (materialId === "" || !quantity) return;

    const clientTransactionUuid = crypto.randomUUID();
    await queueCollection({
      client_transaction_uuid: clientTransactionUuid,
      payload: {
        client_transaction_uuid: clientTransactionUuid,
        material_id: Number(materialId),
        quantity: Number(quantity),
        grade: grade || null,
        collector_name: collectorName || null,
        collector_phone: collectorPhone || null,
      },
      created_at: new Date().toISOString(),
    });

    setQuantity("");
    setGrade("");
    setCollectorName("");
    setCollectorPhone("");
    setJustQueued(true);
    setTimeout(() => setJustQueued(false), 2000);
  }

  if (!user.collection_point_id) {
    return <p>Your account has no assigned collection point — ask an admin to set one.</p>;
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.6rem", maxWidth: 360 }}>
      <h2>Record a collection</h2>
      {materials.length === 0 && <p>No materials cached yet — connect once to load your branch's accepted materials.</p>}
      <label>
        Material
        <select
          value={materialId}
          onChange={(e) => setMaterialId(e.target.value ? Number(e.target.value) : "")}
          required
          style={{ display: "block", width: "100%", padding: "0.5rem" }}
        >
          <option value="">Select material…</option>
          {materials.map((m) => (
            <option key={m.material.id} value={m.material.id}>
              {m.material.name} ({m.material.unit}) — @{m.current_rate.rate}/{m.material.unit}
            </option>
          ))}
        </select>
      </label>
      <label>
        Quantity ({materials.find((m) => m.material.id === materialId)?.material.unit ?? "unit"})
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          required
          style={{ display: "block", width: "100%", padding: "0.5rem" }}
        />
      </label>
      <label>
        Grade / quality (optional)
        <input value={grade} onChange={(e) => setGrade(e.target.value)} style={{ display: "block", width: "100%", padding: "0.5rem" }} />
      </label>
      <label>
        Collector name (optional — walk-in, no registration)
        <input
          value={collectorName}
          onChange={(e) => setCollectorName(e.target.value)}
          style={{ display: "block", width: "100%", padding: "0.5rem" }}
        />
      </label>
      <label>
        Collector phone (optional)
        <input
          value={collectorPhone}
          onChange={(e) => setCollectorPhone(e.target.value)}
          style={{ display: "block", width: "100%", padding: "0.5rem" }}
        />
      </label>
      <button type="submit" style={{ padding: "0.6rem" }}>
        Record collection
      </button>
      {justQueued && <p style={{ color: "green" }}>Queued — will sync automatically.</p>}
    </form>
  );
}
