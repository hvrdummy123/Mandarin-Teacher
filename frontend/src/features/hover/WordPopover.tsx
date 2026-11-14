import { useState } from "react";
import type { Token } from "../../lib/api";
import { label, LABELS } from "../../lib/labels";
import { playTts } from "../../lib/playTts";
import { useUiStore } from "../../lib/store";

type Props = {
  token: Token | null;
  contextSentence: string | null;
  onSave: (token: Token) => void;
  onClose: () => void;
  saved?: boolean;
};

export function WordPopover({ token, contextSentence, onSave, onClose, saved }: Props) {
  const showZh = useUiStore((s) => s.showZhLabels);
  const [playing, setPlaying] = useState<"word" | "sentence" | null>(null);
  const [playError, setPlayError] = useState<string | null>(null);

  if (!token) {
    return (
      <div className="text-sm text-muted">
        Click or focus a word to see meanings.
        {showZh ? <span className="block text-xs">点一个词看看意思。</span> : null}
      </div>
    );
  }

  async function hear(which: "word" | "sentence", text: string) {
    setPlayError(null);
    setPlaying(which);
    try {
      await playTts(text);
    } catch (err) {
      setPlayError(err instanceof Error ? err.message : "Playback failed");
    } finally {
      setPlaying(null);
    }
  }

  return (
    <div className="space-y-3" role="dialog" aria-label={`Word ${token.surface}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-serif text-2xl text-ink">{token.surface}</p>
          <p className="text-sm text-muted">{token.pinyin}</p>
        </div>
        <button type="button" onClick={onClose} className="text-sm text-muted hover:text-ink">
          {label(LABELS.close, showZh)}
        </button>
      </div>
      {token.hsk != null ? (
        <span className="inline-block rounded border border-jade/40 px-2 py-0.5 text-xs text-jade">
          HSK {token.hsk}
        </span>
      ) : null}
      <ul className="space-y-1 text-sm text-ink">
        {token.definitions.slice(0, 3).map((d) => (
          <li key={d}>{d}</li>
        ))}
        {token.definitions.length === 0 ? (
          <li className="text-muted">No dictionary entry for this token.</li>
        ) : null}
      </ul>
      {token.chars.length > 0 ? (
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-muted">Characters</p>
          <ul className="space-y-1 text-sm">
            {token.chars.map((c) => (
              <li key={c.ch}>
                <span className="font-serif">{c.ch}</span>{" "}
                <span className="text-muted">{c.pinyin}</span>
                {c.meaning ? <span className="text-muted"> — {c.meaning}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={playing !== null}
          onClick={() => void hear("word", token.surface)}
          className="rounded border border-jade/50 bg-jade/10 px-3 py-1.5 text-sm text-ink hover:bg-jade/20 disabled:opacity-50"
        >
          {playing === "word" ? "…" : label(LABELS.playWord, showZh)}
        </button>
        {contextSentence ? (
          <button
            type="button"
            disabled={playing !== null}
            onClick={() => void hear("sentence", contextSentence)}
            className="rounded border border-jade/50 bg-jade/10 px-3 py-1.5 text-sm text-ink hover:bg-jade/20 disabled:opacity-50"
          >
            {playing === "sentence" ? "…" : label(LABELS.playSentence, showZh)}
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => onSave(token)}
          disabled={saved}
          className="rounded bg-vermilion px-3 py-1.5 text-sm text-paper hover:opacity-90 disabled:opacity-50"
        >
          {saved ? label(LABELS.saved, showZh) : label(LABELS.save, showZh)}
        </button>
      </div>
      {playError ? (
        <p className="text-xs text-vermilion" role="alert">
          {playError}
        </p>
      ) : null}
      {contextSentence ? <p className="text-xs text-muted">From: {contextSentence}</p> : null}
    </div>
  );
}
