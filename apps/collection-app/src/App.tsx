import { AuthProvider, useAuth, LoginForm } from "@takaflow/ui";
import { CollectionForm } from "./CollectionForm";
import { OutboxStatus } from "./OutboxStatus";

function AuthedApp() {
  const { user, loading, logout } = useAuth();

  if (loading) return null;
  if (!user) return <LoginForm title="TAKAFLOW — Collection App" />;

  return (
    <main style={{ fontFamily: "sans-serif", maxWidth: 600, margin: "2rem auto", padding: "0 1rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
        <h1 style={{ fontSize: "1.5rem", margin: 0, minWidth: 0 }}>TAKAFLOW — Collection App</h1>
        <button onClick={logout} style={{ padding: "0.3rem 0.7rem", flexShrink: 0 }}>
          Sign out
        </button>
      </header>
      <p>
        Signed in as <strong>{user.full_name}</strong> ({user.role})
      </p>

      <CollectionForm user={user} />
      <hr style={{ margin: "2rem 0" }} />
      <OutboxStatus />
    </main>
  );
}

function App() {
  return (
    <AuthProvider>
      <AuthedApp />
    </AuthProvider>
  );
}

export default App;
