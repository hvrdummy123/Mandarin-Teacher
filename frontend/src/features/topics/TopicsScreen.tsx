import { useState } from "react";
import { api } from "../../lib/api";
import { label, LABELS } from "../../lib/labels";
import { useUiStore } from "../../lib/store";

export function TopicsScreen() {
  const showZh = useUiStore((s) => s.showZhLabels);
  const topics = useUiStore((s) => s.topics);
  const level = useUiStore((s) => s.level);
  const setSessionId = useUiStore((s) => s.setSessionId);
  const setMessages = useUiStore((s) => s.setMessages);
  const setTopicId = useUiStore((s) => s.setTopicId);
  const setView = useUiStore((s) => s.setView);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function startTopic(topicId: string) {
    setBusyId(topicId);
    setError(null);
    try {
      const opened = await api.openTopic({ topic_id: topicId, level });
      setTopicId(topicId);
      setSessionId(opened.session.id);
      setMessages([opened.assistant_message]);
      setView("chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start topic");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
      <h1 className="font-serif text-3xl text-ink">{label(LABELS.topicsTitle, showZh)}</h1>
      <p className="mt-2 max-w-xl text-muted">{LABELS.topicsHint.en}</p>
      {showZh ? <p className="text-xs text-muted">{LABELS.topicsHint.zh}</p> : null}
      {error ? (
        <p className="mt-3 text-sm text-vermilion" role="alert">
          {error}
        </p>
      ) : null}
      <ul className="mt-6 space-y-3">
        {topics.map((t) => (
          <li key={t.id}>
            <button
              type="button"
              disabled={busyId === t.id}
              className="w-full rounded border border-muted/30 px-4 py-3 text-left hover:bg-jade/10 disabled:opacity-60"
              onClick={() => void startTopic(t.id)}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-serif text-xl text-ink">
                  {t.title_en}
                  {showZh ? <span className="ml-2 text-base text-muted">{t.title_zh}</span> : null}
                </span>
                <span className="shrink-0 text-xs text-muted">
                  {label(LABELS.suggestedLevel, showZh)} {t.min_level}+
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">{t.user_goal}</p>
              <p className="mt-2 text-xs text-jade">
                {busyId === t.id ? label(LABELS.thinking, showZh) : label(LABELS.start, showZh)}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
