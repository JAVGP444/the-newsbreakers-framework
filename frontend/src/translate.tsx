import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "./api";

export const STORAGE_KEY = "tnb.translateEs";

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
};

const Ctx = createContext<TranslateCtx>({ enabled: false, setEnabled: () => {} });

export function TranslateProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabledState] = useState(readStored);
  const setEnabled = (on: boolean) => {
    writeStored(on);
    setEnabledState(on);
  };
  const value = useMemo(() => ({ enabled, setEnabled }), [enabled]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTranslateEs() {
  return useContext(Ctx);
}

export function useTranslated(texts: string[]): string[] {
  const { enabled } = useTranslateEs();
  const key = texts.join("\u0001");
  const [, bump] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    const missing = [...new Set(texts.filter((t) => t && !cache.has(t)))];
    if (!missing.length) return;
    const batchKey = missing.join("\u0001");
    let pending = inflight.get(batchKey);
    if (!pending) {
      pending = api
        .translate(missing)
        .then((out) => {
          missing.forEach((src, i) => {
            const next = out[i] || src;
            if (next && next !== src) cache.set(src, next);
          });
          return out;
        })
        .finally(() => {
          inflight.delete(batchKey);
        });
      inflight.set(batchKey, pending);
    }
    let cancelled = false;
    pending
      .then(() => {
        if (!cancelled) bump((n) => n + 1);
      })
      .catch(() => {
        /* keep originals */
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, key]);

  if (!enabled) return texts;
  return texts.map((t) => cache.get(t) ?? t);
}

export function TranslateToggle() {
  const { enabled, setEnabled } = useTranslateEs();
  return (
    <label className={`translate-toggle${enabled ? " on" : ""}`}>
      <input
        type="checkbox"
        checked={enabled}
        onChange={(e) => setEnabled(e.target.checked)}
      />
      Traducir al español
    </label>
  );
}
