import type { Token } from "../../lib/api";

type Props = {
  token: Token | null;
  contextSentence: string | null;
  onSave: (token: Token) => void;
  onClose: () => void;
  saved?: boolean;
};

export function WordPopover({ token, contextSentence, onSave, onClose, saved }: Props) {
  if (!token) {
    return (
      <div className="text-sm text-muted">
        点一个词，看看意思。Hover or focus a word.
      </div>
    );
  }

  return (
    <div className="space-y-3" role="dialog" aria-label={`Word ${token.surface}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-serif text-2xl text-ink">{token.surface}</p>
          <p className="text-sm text-muted">{token.pinyin}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-muted hover:text-ink"
          aria-label="Close"
        >
          关闭
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
        {token.definitions.length === 0 ? <li className="text-muted">词典里没有这条。</li> : null}
      </ul>
      {token.chars.length > 0 ? (
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-muted">按字</p>
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
      <div className="flex gap-2">
        <button
          type="button"
          disabled
          title="Voice replay lands with TTS in Phase 2"
          className="rounded border border-muted/40 px-3 py-1.5 text-sm text-muted opacity-60"
        >
          播放
        </button>
        <button
          type="button"
          onClick={() => onSave(token)}
          disabled={saved}
          className="rounded bg-vermilion px-3 py-1.5 text-sm text-paper hover:opacity-90 disabled:opacity-50"
        >
          {saved ? "已保存" : "收藏"}
        </button>
      </div>
      {contextSentence ? (
        <p className="text-xs text-muted">出处：{contextSentence}</p>
      ) : null}
    </div>
  );
}
