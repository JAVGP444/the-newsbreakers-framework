import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { interpolate, lookup, type Lang } from "./i18n";

const STORAGE_KEY = "tnb.lang";

function readLang(): Lang {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "en" || raw === "es") return raw;
  } catch {
    /* ignore */
  }
  return "es";
}

type Ctx = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const LocaleCtx = createContext<Ctx>({
  lang: "es",
  setLang: () => {},
  t: (key, vars) => interpolate(key, vars),
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readLang);

  const setLang = (next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const value = useMemo(
    () => ({
      lang,
      setLang,
      t: (key: string, vars?: Record<string, string | number>) => lookup(lang, key, vars),
    }),
    [lang]
  );

  return <LocaleCtx.Provider value={value}>{children}</LocaleCtx.Provider>;
}

export function useLocale() {
  return useContext(LocaleCtx);
}

export function LanguageToggle() {
  const { lang, setLang, t } = useLocale();
  return (
    <div className="lang-switch" role="group" aria-label={t("lang.aria")}>
      <button type="button" className={lang === "es" ? "on" : ""} onClick={() => setLang("es")}>
        ES
      </button>
      <button type="button" className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>
        EN
      </button>
    </div>
  );
}
