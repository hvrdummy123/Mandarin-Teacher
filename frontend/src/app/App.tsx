import { useEffect } from "react";
import { Shell } from "../components/Shell";
import { useUiStore } from "../lib/store";
import { applyTheme } from "../lib/theme";

declare global {
  interface Window {
    __DUIHUA_STORE__?: typeof useUiStore;
  }
}

export function App() {
  const theme = useUiStore((s) => s.theme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    // Used by portfolio / e2e recorders only (`?demo=portfolio`).
    if (new URLSearchParams(window.location.search).get("demo") === "portfolio") {
      window.__DUIHUA_STORE__ = useUiStore;
    }
  }, []);

  return <Shell />;
}
