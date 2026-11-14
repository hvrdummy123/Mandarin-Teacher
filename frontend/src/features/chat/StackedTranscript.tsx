import type { Token } from "../../lib/api";
import { toneOfPinyin, TONE_CLASS } from "../../lib/tones";

type Props = {
  tokens: Token[] | null | undefined;
  text: string;
  translation?: string | null;
  showPinyin: boolean;
  showHanzi: boolean;
  showEnglish: boolean;
  onSelectToken?: (token: Token) => void;
  activeToken?: Token | null;
  /** Live / interim draft styling */
  live?: boolean;
};

/** Airlearn-style stack: pinyin on top, hanzi large, English under. */
export function StackedTranscript({
  tokens,
  text,
  translation,
  showPinyin,
  showHanzi,
  showEnglish,
  onSelectToken,
  activeToken,
  live,
}: Props) {
  const pinyinLine =
    tokens && tokens.length > 0
      ? tokens
          .map((t) => t.pinyin || (t.surface.match(/[\u4e00-\u9fff]/) ? "" : t.surface))
          .filter(Boolean)
          .join(" ")
      : "";

  return (
    <div className={`space-y-1.5 ${live ? "opacity-90" : ""}`}>
      {showPinyin && pinyinLine ? (
        <p className="font-sans text-sm tracking-wide text-muted" lang="zh-Latn">
          {pinyinLine}
        </p>
      ) : null}

      {showHanzi ? (
        tokens && tokens.length > 0 && onSelectToken ? (
          <p className="font-serif text-2xl leading-relaxed text-ink md:text-[1.65rem]">
            {tokens.map((token, i) => {
              const isActive = activeToken === token;
              const hasPy = Boolean(token.pinyin);
              return (
                <button
                  key={`${token.surface}-${i}`}
                  type="button"
                  className={`mr-1 inline-block rounded px-0.5 align-baseline focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion ${
                    isActive ? "bg-jade/20" : "hover:bg-jade/10"
                  } ${token.out_of_level ? "underline decoration-dotted decoration-muted" : ""} ${
                    !hasPy ? "font-sans text-xl" : ""
                  }`}
                  onClick={() => onSelectToken(token)}
                  aria-label={
                    token.pinyin ? `${token.surface} ${token.pinyin}` : token.surface
                  }
                >
                  {hasPy ? (
                    <span className={TONE_CLASS[toneOfPinyin(token.pinyin.split(/\s+/)[0] ?? "")]}>
                      {token.surface}
                    </span>
                  ) : (
                    token.surface
                  )}
                </button>
              );
            })}
          </p>
        ) : (
          <p className="font-serif text-2xl leading-relaxed text-ink md:text-[1.65rem]">{text}</p>
        )
      ) : null}

      {showEnglish ? (
        <p className={`text-sm ${live && !translation ? "italic text-muted/70" : "text-muted"}`}>
          {translation || (live ? "…" : null)}
        </p>
      ) : null}
    </div>
  );
}
