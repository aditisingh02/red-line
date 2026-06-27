import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type User = {
  id: string;
  github_id: number;
  github_login: string;
  name: string;
  email: string;
  avatar_url: string;
};

type AuthState = {
  user: User | null;
  loading: boolean;
  authEnabled: boolean | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authEnabled, setAuthEnabled] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [h, me] = await Promise.all([
        fetch("/api/health").then((r) => (r.ok ? r.json() : null)),
        fetch("/api/auth/me").then((r) => (r.ok ? r.json() : null)),
      ]);
      setAuthEnabled(h ? Boolean(h.auth_enabled) : false);
      setUser(me);
    } catch {
      setAuthEnabled(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    setUser(null);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <AuthContext.Provider value={{ user, loading, authEnabled, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

/** Kick off a redirect to the backend OAuth login. */
export function loginWithGitHub(): void {
  window.location.href = "/api/auth/github/login";
}
