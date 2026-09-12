import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";

export const STORAGE_KEY = "tnb.translateEs";
const CHUNK = 8;

const cache = new Map<string, string>();
const inflight = new Map<string, Promise<string[]>>();

function readStored(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw === "1" || raw === "true";
  } catch {
    return false;
  }
}

function writeStored(on: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "1" : "0");
  } catch {
    /* ignore quota / private mode */
  }
}

type TranslateCtx = {
  enabled: boolean;
  setEnabled: (on: boolean) => void;
  busy: number;
  error: string;
  begin: () => void;
  end: () => void;
  fail: (msg: string) => void;
};

const Ctx = createContext<TranslateCtx>({
  enabled: false,
  setEnabled: () => {},
  busy: 0,
  error: "",
  begin: () => {},
  end: () => {},
  fail: () => {},
});

export function TranslateProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabledState] = useState(readStored);
  const [busy, setBusy] = useState(0);
  const [error, setError] = useState("");
  const setEnabled = (on: boolean) => {
    writeStored(on);
    if (on) {
      cache.clear();
      inflight.clear();
      setError("");
    }
    setEnabledState(on);
  };
  const value = useMemo(
    () => ({
      enabled,
      setEnabled,
      busy,
      error,
      begin: () => setBusy((n) => n + 1),
      end: () => setBusy((n) => Math.max(0, n - 1)),
      fail: (msg: string) => setError(msg),
    }),
    [enabled, busy, error]
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTranslateEs() {
  return useContext(Ctx);
}

async function translateChunked(texts: string[]): Promise<string[]> {
  const unique = [...new Set(texts.filter((t) => t))];
  const map = new Map<string, string>();
  for (let i = 0; i < unique.length; i += CHUNK) {
    const slice = unique.slice(i, i + CHUNK);
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => ctrl.abort(), 25000);
    try {
      const got = await api.translate(slice, ctrl.signal);
      slice.forEach((src, j) => {
        const next = got[j] || "";
        if (next && next !== src) map.set(src, next);
      });
    } finally {
      window.clearTimeout(timer);
    }
  }
  return texts.map((t) => map.get(t) || t);
}

export function useTranslated(texts: string[]): string[] {
  const { enabled, begin, end, fail } = useTranslateEs();
  const key = texts.join("\u0001");
  const [, bump] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    const missing = [...new Set(texts.filter((t) => t && !cache.has(t)))];
    if (!missing.length) return;
    const batchKey = missing.join("\u0001");
    let pending = inflight.get(batchKey);
    if (!pending) {
      begin();
      pending = translateChunked(missing)
        .then((out) => {
          missing.forEach((src, i) => {
            const next = out[i] || "";
            if (next && next !== src) cache.set(src, next);
          });
          fail("");
          return out;
        })
        .catch(() => {
          fail("No se pudo traducir. Reintenta el interruptor.");
          return missing;
        })
        .finally(() => {
          inflight.delete(batchKey);
          end();
        });
      inflight.set(batchKey, pending);
    }
    let cancelled = false;
    pending.then(() => {
      if (!cancelled) bump((n) => n + 1);
    });
    return () => {
      cancelled = true;
    };
  }, [enabled, key]);

  if (!enabled) return texts;
  return texts.map((t) => cache.get(t) ?? t);
}

export function TranslateToggle() {
  const { enabled, setEnabled, busy, error } = useTranslateEs();
  const label = !enabled ? "Traducir al español" : busy > 0 ? "Traduciendo…" : error ? "Error al traducir" : "Traducir al español";
  return (
    <label className={`translate-toggle${enabled ? " on" : ""}${error ? " err" : ""}`} title={error || undefined}>
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => setEnabled(e.target.checked)}
      />
      {label}
    </label>
  );
}
