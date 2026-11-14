import { toneOfPinyin, TONE_CLASS } from "../../lib/tones";
import type { Token } from "../../lib/api";

type Props = {
  tokens: Token[];
  showPinyin: boolean;
  showHanzi: boolean;
  onSelect: (token: Token) => void;
  active?: Token | null;
};

export function RubyText({ tokens, showPinyin, showHanzi, onSelect, active }: Props) {
  return (
    <p className="font-serif text-hanzi leading-loose">
      {tokens.map((token, i) => {
        if (!token.pinyin) {
          return (
            <span key={`${token.surface}-${i}`} className="font-sans text-base">
              {token.surface}
            </span>
          );
        }
        const syllables = token.pinyin.split(/\s+/);
        const tone = toneOfPinyin(syllables[0] ?? "");
        const isActive = active?.surface === token.surface && active === token;
        return (
          <button
            key={`${token.surface}-${i}`}
            type="button"
            className={`mx-0.5 inline-block rounded px-0.5 align-baseline focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion ${
              isActive ? "bg-jade/15" : "hover:bg-jade/10"
            } ${token.out_of_level ? "underline decoration-dotted decoration-muted" : ""}`}
            onClick={() => onSelect(token)}
            onFocus={() => onSelect(token)}
            aria-label={`${token.surface} ${token.pinyin}`}
          >
            <ruby className={!showHanzi ? "opacity-0" : undefined}>
              <span className={!showHanzi ? "select-none" : undefined}>{token.surface}</span>
              {showPinyin ? (
                <rt className={`text-[0.55em] font-sans ${TONE_CLASS[tone]}`}>
                  {token.pinyin}
                </rt>
              ) : null}
            </ruby>
          </button>
        );
      })}
    </p>
  );
}
