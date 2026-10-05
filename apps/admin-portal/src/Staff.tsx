import { useState } from "react";
import { CreateStaffForm } from "./CreateStaffForm";
import { StaffList } from "./StaffList";

export function Staff() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      <CreateStaffForm onCreated={() => setRefreshKey((k) => k + 1)} />
      <StaffList
        refreshKey={refreshKey}
        role="collection_point_staff"
        title="Staff across branches"
        description="Deactivating an account blocks it from signing in immediately — their past collections and payments stay on record. Reactivate any time."
        emptyLabel="No staff accounts yet."
      />
      <StaffList
        refreshKey={refreshKey}
        role="admin"
        title="Admins"
        description="Deactivating an admin account blocks it from signing in immediately. Reactivate any time."
        emptyLabel="No other admin accounts yet."
      />
    </div>
  );
}
