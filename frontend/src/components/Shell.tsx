import { useEffect, useState } from "react";
import { api, type Message, type Token } from "../lib/api";
import { useUiStore } from "../lib/store";
import { ChatPanel } from "../features/chat/ChatPanel";
import { WordPopover } from "../features/hover/WordPopover";

const NAV = [
  { id: "chat", label: "对话" },
  { id: "topics", label: "话题" },
  { id: "words", label: "生词" },
  { id: "progress", label: "进度" },
] as const;

export function Shell() {
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
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
  const topicId = useUiStore((s) => s.topicId);
  const setTopicId = useUiStore((s) => s.setTopicId);
  const topics = useUiStore((s) => s.topics);
  const setTopics = useUiStore((s) => s.setTopics);
  const sessionId = useUiStore((s) => s.sessionId);
  const setSessionId = useUiStore((s) => s.setSessionId);
  const messages = useUiStore((s) => s.messages);
  const setMessages = useUiStore((s) => s.setMessages);
  const appendMessages = useUiStore((s) => s.appendMessages);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<Token | null>(null);
  const [activeMsg, setActiveMsg] = useState<Message | null>(null);
  const [savedNote, setSavedNote] = useState(false);
  const [view, setView] = useState<"chat" | "topics" | "words">("chat");
  const [savedWords, setSavedWords] = useState<
    { id: number; word: string; pinyin: string; definition: string }[]
  >([]);

  useEffect(() => {
    api.topics().then(setTopics).catch(() => setTopics([]));
  }, [setTopics]);

  const selectedTopic = topics.find((t) => t.id === topicId);
  const levelWarn =
    selectedTopic && level < selectedTopic.min_level
      ? `这个话题建议等级 ${selectedTopic.min_level}+，你现在是 ${level}。可以试试，只是会难一点。`
      : null;

  async function ensureSession(): Promise<number> {
    if (sessionId != null) return sessionId;
    const session = await api.createSession({
      mode: topicId ? "topic" : "free",
      topic_id: topicId,
      level,
    });
    setSessionId(session.id);
    return session.id;
  }

  async function restartSession() {
    setMessages([]);
    setSessionId(null);
    setActive(null);
    setError(null);
  }

  async function onSend(text: string) {
    setBusy(true);
    setError(null);
    try {
      // New session if level/topic changed mid-chat — simplest honest approach.
      const sid = await ensureSession();
      const turn = await api.sendMessage(sid, text);
      appendMessages([turn.user_message, turn.assistant_message]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败，稍后再试。");
    } finally {
      setBusy(false);
    }
  }

  async function onSave(token: Token) {
    try {
      await api.saveWord({
        word: token.surface,
        pinyin: token.pinyin,
        definition: token.definitions[0] ?? "",
        hsk_level: token.hsk,
        context_sentence: activeMsg?.text ?? null,
      });
      setSavedNote(true);
      setTimeout(() => setSavedNote(false), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "收藏失败");
    }
  }

  async function openWords() {
    setView("words");
    try {
      const list = await api.listWords();
      setSavedWords(list);
    } catch {
      setSavedWords([]);
    }
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside
        className="hidden w-52 shrink-0 border-r border-muted/30 bg-paper/80 p-4 md:flex md:flex-col"
        aria-label="Main"
      >
        <div className="mb-8">
          <p className="font-serif text-2xl tracking-tight text-ink">对话</p>
          <p className="text-sm text-muted">duihua</p>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                if (item.id === "words") void openWords();
                else if (item.id === "topics") setView("topics");
                else setView("chat");
              }}
              className="rounded px-3 py-2 text-left text-sm text-ink hover:bg-jade/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="mt-6 space-y-3 border-t border-muted/30 pt-4 text-sm">
          <label className="block text-muted">
            等级档 {tier}
            <input
              type="range"
              min={1}
              max={10}
              value={tier}
              onChange={(e) => {
                setTier(Number(e.target.value));
                void restartSession();
              }}
              className="mt-1 w-full"
            />
          </label>
          <label className="block text-muted">
            精细等级 {level}
            <input
              type="range"
              min={(tier - 1) * 10 + 1}
              max={tier * 10}
              value={level}
              onChange={(e) => {
                setLevel(Number(e.target.value));
                void restartSession();
              }}
              className="mt-1 w-full"
            />
          </label>
          <label className="block text-muted">
            话题
            <select
              className="mt-1 w-full rounded border border-muted/40 bg-paper px-2 py-1 text-ink"
              value={topicId ?? ""}
              onChange={(e) => {
                setTopicId(e.target.value || null);
                void restartSession();
              }}
            >
              <option value="">自由聊天</option>
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title_zh}
                </option>
              ))}
            </select>
          </label>
          {levelWarn ? <p className="text-xs text-vermilion">{levelWarn}</p> : null}
        </div>

        <button
          type="button"
          onClick={toggleTheme}
          className="mt-auto rounded border border-muted/40 px-3 py-2 text-sm text-muted hover:border-jade hover:text-ink"
          aria-label={theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
        >
          {theme === "light" ? "深色" : "浅色"}
        </button>
      </aside>

      <main className="flex min-h-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-2 border-b border-muted/30 px-4 py-3 md:px-8">
          <div className="md:hidden">
            <p className="font-serif text-xl text-ink">对话</p>
          </div>
          <div className="ml-auto flex flex-wrap gap-2 text-sm">
            <Toggle label="拼音" on={showPinyin} onClick={togglePinyin} />
            <Toggle label="汉字" on={showHanzi} onClick={toggleHanzi} />
            <Toggle label="英文" on={showEnglish} onClick={toggleEnglish} />
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded border border-muted/40 px-2 py-1 text-muted md:hidden"
            >
              {theme === "light" ? "深色" : "浅色"}
            </button>
          </div>
        </header>

        {error ? (
          <p className="bg-vermilion/10 px-4 py-2 text-sm text-vermilion" role="alert">
            {error}
          </p>
        ) : null}

        {view === "chat" ? (
          <ChatPanel
            messages={messages}
            showPinyin={showPinyin}
            showHanzi={showHanzi}
            showEnglish={showEnglish}
            busy={busy}
            onSend={onSend}
            activeToken={active}
            onSelectToken={(token, message) => {
              setActive(token);
              setActiveMsg(message);
            }}
          />
        ) : null}

        {view === "topics" ? (
          <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
            <h2 className="mb-4 font-serif text-2xl">话题</h2>
            <ul className="space-y-3">
              {topics.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    className="w-full rounded border border-muted/30 px-3 py-2 text-left hover:bg-jade/10"
                    onClick={() => {
                      setTopicId(t.id);
                      void restartSession();
                      setView("chat");
                    }}
                  >
                    <span className="font-serif text-lg">{t.title_zh}</span>
                    <span className="ml-2 text-sm text-muted">{t.title_en}</span>
                    <p className="text-xs text-muted">建议等级 {t.min_level}+</p>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {view === "words" ? (
          <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
            <h2 className="mb-4 font-serif text-2xl">生词</h2>
            {savedWords.length === 0 ? (
              <p className="text-muted">还没有收藏。点对话里的词再点「收藏」。</p>
            ) : (
              <ul className="space-y-2">
                {savedWords.map((w) => (
                  <li key={w.id} className="border-b border-muted/20 py-2">
                    <span className="font-serif text-xl">{w.word}</span>{" "}
                    <span className="text-sm text-muted">{w.pinyin}</span>
                    <p className="text-sm">{w.definition}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
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
  label,
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
      {label}
    </button>
  );
}
