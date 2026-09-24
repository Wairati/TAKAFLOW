import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionPointOut } from "@takaflow/types";

/** Staff only ever have one branch (collection_point_id) — this resolves its
 * full record (name, hours, etc.) from the collection-points list every app
 * has access to, rather than adding a new single-point endpoint. */
export function useBranch(collectionPointId: number | null): CollectionPointOut | null {
  const [branch, setBranch] = useState<CollectionPointOut | null>(null);

  useEffect(() => {
    if (collectionPointId === null) {
      setBranch(null);
      return;
    }
    api
      .listCollectionPoints()
      .then((points) => setBranch(points.find((p) => p.id === collectionPointId) ?? null))
      .catch(() => setBranch(null));
  }, [collectionPointId]);

  return branch;
}
