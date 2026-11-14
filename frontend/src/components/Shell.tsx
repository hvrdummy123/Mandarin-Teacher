import { useEffect, useState } from "react";
import { api, type Message, type Token } from "../lib/api";
import { label, LABELS } from "../lib/labels";
import { useUiStore, type View } from "../lib/store";
import { ChatScreen } from "../features/chat/ChatScreen";
import { WordPopover } from "../features/hover/WordPopover";
import { ProgressScreen } from "../features/progress/ProgressScreen";
import { TopicsScreen } from "../features/topics/TopicsScreen";
import { WordsScreen } from "../features/words/WordsScreen";

const NAV: { id: View; item: { en: string; zh: string } }[] = [
  { id: "chat", item: LABELS.chat },
  { id: "topics", item: LABELS.topics },
  { id: "words", item: LABELS.words },
  { id: "progress", item: LABELS.progress },
];

export function Shell() {
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
  const showZh = useUiStore((s) => s.showZhLabels);
  const toggleZhLabels = useUiStore((s) => s.toggleZhLabels);
  const showPinyin = useUiStore((s) => s.showPinyin);
  const showHanzi = useUiStore((s) => s.showHanzi);
  const showEnglish = useUiStore((s) => s.showEnglish);
  const togglePinyin = useUiStore((s) => s.togglePinyin);
  const toggleHanzi = useUiStore((s) => s.toggleHanzi);
  const toggleEnglish = useUiStore((s) => s.toggleEnglish);
  const level = useUiStore((s) => s.level);
  const tier = useUiStore((s) => s.tier);
  const setLevel = useUiStore((s) => s.setLevel);
  const setTier = useUiStore((s) => s.setTier);
  const view = useUiStore((s) => s.view);
  const setView = useUiStore((s) => s.setView);
  const setTopics = useUiStore((s) => s.setTopics);

  const [active, setActive] = useState<Token | null>(null);
  const [activeMsg, setActiveMsg] = useState<Message | null>(null);
  const [savedNote, setSavedNote] = useState(false);

  useEffect(() => {
    api.topics().then(setTopics).catch(() => setTopics([]));
  }, [setTopics]);

  async function onSave(token: Token) {
    await api.saveWord({
      word: token.surface,
      pinyin: token.pinyin,
      definition: token.definitions[0] ?? "",
      hsk_level: token.hsk,
      context_sentence: activeMsg?.text ?? null,
    });
    setSavedNote(true);
    setTimeout(() => setSavedNote(false), 1500);
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside
        className="hidden w-56 shrink-0 border-r border-muted/30 bg-paper/80 p-4 md:flex md:flex-col"
        aria-label="Main"
      >
        <div className="mb-8">
          <p className="font-serif text-2xl tracking-tight text-ink">
            {LABELS.brand.en}
            {showZh ? <span className="ml-2 text-lg text-muted">{LABELS.brand.zh}</span> : null}
          </p>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setView(item.id)}
              aria-current={view === item.id ? "page" : undefined}
              className={`rounded px-3 py-2 text-left text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion ${
                view === item.id ? "bg-jade/15 text-ink" : "text-ink hover:bg-jade/10"
              }`}
            >
              {label(item.item, showZh)}
            </button>
          ))}
        </nav>

        <div className="mt-6 space-y-3 border-t border-muted/30 pt-4 text-sm">
          <label className="block text-muted">
            {label(LABELS.tier, showZh)} {tier}
            <input
              type="range"
              min={1}
              max={10}
              value={tier}
              onChange={(e) => setTier(Number(e.target.value))}
              className="mt-1 w-full"
            />
          </label>
          <label className="block text-muted">
            {label(LABELS.level, showZh)} {level}
            <input
              type="range"
              min={(tier - 1) * 10 + 1}
              max={tier * 10}
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="mt-1 w-full"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={toggleZhLabels}
          className="mt-4 rounded border border-muted/40 px-3 py-2 text-left text-sm text-muted"
        >
          {label(showZh ? LABELS.hideZh : LABELS.showZh, false)}
        </button>
        <button
          type="button"
          onClick={toggleTheme}
          className="mt-2 rounded border border-muted/40 px-3 py-2 text-sm text-muted"
        >
          {label(theme === "light" ? LABELS.dark : LABELS.light, showZh)}
        </button>
      </aside>

      <main className="flex min-h-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-2 border-b border-muted/30 px-4 py-3 md:px-8">
          <p className="font-serif text-xl text-ink md:hidden">{LABELS.brand.en}</p>
          <div className="ml-auto flex flex-wrap gap-2 text-sm">
            <Toggle label={label(LABELS.pinyin, showZh)} on={showPinyin} onClick={togglePinyin} />
            <Toggle label={label(LABELS.hanzi, showZh)} on={showHanzi} onClick={toggleHanzi} />
            <Toggle
              label={label(LABELS.english, showZh)}
              on={showEnglish}
              onClick={toggleEnglish}
            />
          </div>
        </header>

        {view === "chat" ? (
          <ChatScreen
            activeToken={active}
            onSelectToken={(token, message) => {
              setActive(token);
              setActiveMsg(message);
            }}
          />
        ) : null}
        {view === "topics" ? <TopicsScreen /> : null}
        {view === "words" ? <WordsScreen /> : null}
        {view === "progress" ? <ProgressScreen /> : null}

        <nav
          className="flex justify-around border-t border-muted/30 p-2 md:hidden"
          aria-label="Mobile"
        >
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className="px-2 py-1 text-xs text-muted"
              onClick={() => setView(item.id)}
            >
              {item.item.en}
            </button>
          ))}
        </nav>
      </main>

      <aside
        className="hidden w-72 shrink-0 border-l border-muted/30 bg-paper/60 p-4 lg:block"
        aria-label="Details"
      >
        <WordPopover
          token={active}
          contextSentence={activeMsg?.text ?? null}
          onSave={onSave}
          onClose={() => setActive(null)}
          saved={savedNote}
        />
      </aside>
    </div>
  );
}

function Toggle({
  label: name,
  on,
  onClick,
}: {
  label: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={`rounded border px-2 py-1 ${
        on ? "border-jade bg-jade/10 text-ink" : "border-muted/40 text-muted"
      }`}
    >
      {name}
    </button>
  );
}
