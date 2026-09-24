import { useEffect, useState } from "react";
import { api } from "@takaflow/ui";
import type { CollectionPointOut } from "@takaflow/types";

export function useCollectionPoints() {
  const [points, setPoints] = useState<CollectionPointOut[]>([]);
  useEffect(() => {
    api.listCollectionPoints().then(setPoints).catch(() => setPoints([]));
  }, []);
  const nameById = new Map(points.map((p) => [p.id, p.name]));
  return { points, nameById };
}
