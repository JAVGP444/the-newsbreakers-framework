import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setSessionToken, sessionToken, type AccountInfo, type LicenseInfo } from "./api";

type Ctx = {
  info: LicenseInfo | null;
  account: AccountInfo | null;
  licensed: boolean;
  signedIn: boolean;
  loading: boolean;
  refresh: () => Promise<void>;
  activate: (key: string) => Promise<LicenseInfo>;
  login: (email: string, password: string, key?: string) => Promise<AccountInfo>;
  register: (email: string, password: string, key?: string) => Promise<AccountInfo>;
  logout: () => Promise<void>;
};

const LicenseCtx = createContext<Ctx>({
  info: null,
  account: null,
  licensed: false,
  signedIn: false,
  loading: true,
  refresh: async () => {},
  activate: async () => {
    throw new Error("license");
  },
  login: async () => {
    throw new Error("login");
  },
  register: async () => {
    throw new Error("register");
  },
  logout: async () => {},
});

export function LicenseProvider({ children }: { children: ReactNode }) {
  const [info, setInfo] = useState<LicenseInfo | null>(null);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const lic = await api.license();
      setInfo(lic);
    } catch {
      setInfo(null);
    }
    if (!sessionToken()) {
      setAccount(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setAccount(me);
      if (me.license) setInfo(me.license);
    } catch {
      setSessionToken(null);
      setAccount(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const activate = async (key: string) => {
    const next = await api.activateLicense(key.trim());
    setInfo(next);
    await refresh();
    return next;
  };

  const login = async (email: string, password: string, key = "") => {
    const next = await api.login(email, password, key);
    if (next.session) setSessionToken(next.session);
    setAccount(next);
    if (next.license) setInfo(next.license);
    await refresh();
    return next;
  };

  const register = async (email: string, password: string, key = "") => {
    const next = await api.register(email, password, key);
    if (next.session) setSessionToken(next.session);
    setAccount(next);
    if (next.license) setInfo(next.license);
    await refresh();
    return next;
  };

  const logout = async () => {
    await api.logout();
    setAccount(null);
    try {
      setInfo(await api.license());
    } catch {
      setInfo(null);
    }
  };

  return (
    <LicenseCtx.Provider
      value={{
        info,
        account,
        licensed: Boolean(account?.licensed),
        signedIn: Boolean(account?.ok),
        loading,
        refresh,
        activate,
        login,
        register,
        logout,
      }}
    >
      {children}
    </LicenseCtx.Provider>
  );
}

export function useLicense() {
  return useContext(LicenseCtx);
}
