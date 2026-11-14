import { useState } from "react";
import { label, LABELS } from "../../lib/labels";
import { playTts } from "../../lib/playTts";
import { useUiStore } from "../../lib/store";

type Props = {
  original: string;
  better: string;
  reason: string;
};

export function CorrectionCard({ original, better, reason }: Props) {
  const showZh = useUiStore((s) => s.showZhLabels);
  const [playing, setPlaying] = useState(false);

  return (
    <aside
      className="mt-2 rounded-xl border border-jade/40 bg-jade/5 px-3 py-3 text-sm"
      aria-label="Suggestion"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-jade">
        {label(LABELS.suggestion, showZh)}
      </p>
      <p className="mt-1 text-muted line-through decoration-muted/60">{original}</p>
      <div className="mt-1 flex items-start gap-2">
        <p className="flex-1 font-serif text-lg text-ink">{better}</p>
        <button
          type="button"
          disabled={playing}
          title={label(LABELS.playCorrection, showZh)}
          aria-label={label(LABELS.playCorrection, showZh)}
          className="shrink-0 rounded-full border border-jade/50 bg-paper px-2.5 py-1 text-xs text-jade hover:bg-jade/10 disabled:opacity-50"
          onClick={() => {
            setPlaying(true);
            void playTts(better).finally(() => setPlaying(false));
          }}
        >
          {playing ? "…" : "▶"}
        </button>
      </div>
      <p className="mt-2 text-xs text-muted">{reason}</p>
    </aside>
  );
}
