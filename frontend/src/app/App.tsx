import { useEffect } from "react";
import { Shell } from "../components/Shell";
import { useUiStore } from "../lib/store";
import { applyTheme } from "../lib/theme";

export function App() {
  const theme = useUiStore((s) => s.theme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return <Shell />;
}
