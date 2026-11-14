import { useUiStore } from "../lib/store";

const NAV = [
  { id: "chat", label: "对话" },
  { id: "topics", label: "话题" },
  { id: "words", label: "生词" },
  { id: "progress", label: "进度" },
] as const;

export function Shell() {
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside
        className="hidden w-48 shrink-0 border-r border-muted/30 bg-paper/80 p-4 md:flex md:flex-col"
        aria-label="Main"
      >
        <div className="mb-8">
          <p className="font-serif text-2xl tracking-tight text-ink">对话</p>
          <p className="text-sm text-muted">duihua</p>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className="rounded px-3 py-2 text-left text-sm text-ink hover:bg-jade/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <button
          type="button"
          onClick={toggleTheme}
          className="mt-4 rounded border border-muted/40 px-3 py-2 text-sm text-muted hover:border-jade hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion"
          aria-label={theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
        >
          {theme === "light" ? "深色" : "浅色"}
        </button>
      </aside>

      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-muted/30 px-4 py-3 md:px-8">
          <div className="md:hidden">
            <p className="font-serif text-xl text-ink">对话</p>
          </div>
          <p className="hidden text-sm text-muted md:block">说得慢一点也没关系。加油。</p>
          <button
            type="button"
            onClick={toggleTheme}
            className="rounded border border-muted/40 px-3 py-1.5 text-sm text-muted md:hidden"
            aria-label="Toggle theme"
          >
            {theme === "light" ? "深色" : "浅色"}
          </button>
        </header>

        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-16 text-center">
          <h1 className="font-serif text-3xl text-ink md:text-4xl">准备好了再说</h1>
          <p className="max-w-md text-muted">
            选一个话题，按住麦克风开始。语音和纠音会在后面几轮加上；现在你看到的是壳子和主题。
          </p>
        </div>

        <div className="flex items-center justify-center border-t border-muted/30 p-4 md:hidden">
          <nav className="flex gap-4" aria-label="Mobile">
            {NAV.map((item) => (
              <span key={item.id} className="text-sm text-muted">
                {item.label}
              </span>
            ))}
          </nav>
        </div>
      </main>

      <aside
        className="hidden w-64 shrink-0 border-l border-muted/30 bg-paper/60 p-4 lg:block"
        aria-label="Details"
      >
        <p className="text-sm text-muted">词义、声调、本回合统计会出现在这里。</p>
      </aside>
    </div>
  );
}
