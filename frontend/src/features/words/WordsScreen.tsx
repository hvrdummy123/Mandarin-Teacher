import { useEffect, useState } from "react";
import { api, type SavedWord } from "../../lib/api";
import { label, LABELS } from "../../lib/labels";
import { useUiStore } from "../../lib/store";

export function WordsScreen() {
  const showZh = useUiStore((s) => s.showZhLabels);
  const [words, setWords] = useState<SavedWord[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load(query?: string) {
    try {
      setWords(await api.listWords(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load words");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
      <h1 className="font-serif text-3xl text-ink">{label(LABELS.words, showZh)}</h1>
      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void load(q.trim() || undefined);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={label(LABELS.search, showZh)}
          className="flex-1 rounded border border-muted/40 bg-paper px-3 py-2 text-sm"
          aria-label="Search saved words"
        />
        <button type="submit" className="rounded border border-muted/40 px-3 py-2 text-sm">
          {label(LABELS.search, showZh)}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-vermilion">{error}</p> : null}
      {words.length === 0 ? (
        <p className="mt-6 text-muted">{label(LABELS.wordsEmpty, showZh)}</p>
      ) : (
        <ul className="mt-6 space-y-3">
          {words.map((w) => (
            <li
              key={w.id}
              className="flex items-start justify-between gap-3 border-b border-muted/20 py-3"
            >
              <div>
                <span className="font-serif text-xl">{w.word}</span>{" "}
                <span className="text-sm text-muted">{w.pinyin}</span>
                <p className="text-sm">{w.definition}</p>
                {w.context_sentence ? (
                  <p className="text-xs text-muted">{w.context_sentence}</p>
                ) : null}
              </div>
              <button
                type="button"
                className="text-sm text-vermilion"
                onClick={async () => {
                  await api.deleteWord(w.id);
                  void load(q.trim() || undefined);
                }}
              >
                {label(LABELS.delete, showZh)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
