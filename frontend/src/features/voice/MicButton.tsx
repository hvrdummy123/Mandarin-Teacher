import { label, LABELS } from "../../lib/labels";
import { useUiStore } from "../../lib/store";

type Props = {
  disabled?: boolean;
  /** Tap once to start, tap again when done (Airlearn-style). */
  onToggle: () => void;
};

const STATE_COPY: Record<string, string> = {
  idle: "Tap to speak",
  listening: "Listening… tap when done",
  thinking: "Thinking…",
  speaking: "Speaking…",
  error: "Mic error — tap to retry",
};

export function MicButton({ disabled, onToggle }: Props) {
  const showZh = useUiStore((s) => s.showZhLabels);
  const micState = useUiStore((s) => s.micState);

  const listening = micState === "listening";
  const busy = micState === "thinking" || micState === "speaking";

  return (
    <div className="flex flex-col items-center gap-3 py-3">
      {listening ? (
        <div className="flex h-8 w-full max-w-sm items-center justify-center px-4" aria-hidden>
          <Waveform />
        </div>
      ) : (
        <div className="h-8" />
      )}

      <button
        type="button"
        disabled={disabled || busy}
        aria-label={label(LABELS.mic, showZh)}
        aria-pressed={listening}
        className={`relative flex h-24 w-24 items-center justify-center rounded-full border-4 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion disabled:opacity-50 ${
          listening
            ? "scale-105 border-jade bg-jade text-paper shadow-lg shadow-jade/30"
            : "border-jade/50 bg-jade/15 text-ink hover:bg-jade/25"
        }`}
        onClick={() => onToggle()}
      >
        <MicIcon />
        {listening ? (
          <span className="absolute inset-0 animate-ping rounded-full border-2 border-jade/40" />
        ) : null}
      </button>

      <p className="text-sm text-muted">{STATE_COPY[micState] ?? "Ready"}</p>
      <p className="text-xs text-muted">
        {listening ? label(LABELS.micDone, showZh) : label(LABELS.micTap, showZh)}
      </p>
    </div>
  );
}

function Waveform() {
  return (
    <svg viewBox="0 0 240 32" className="h-8 w-full text-jade" fill="none">
      <path
        className="motion-safe:animate-pulse"
        d="M0 16 Q20 4 40 16 T80 16 T120 16 T160 16 T200 16 T240 16"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M19 11a7 7 0 0 1-14 0M12 18v3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
