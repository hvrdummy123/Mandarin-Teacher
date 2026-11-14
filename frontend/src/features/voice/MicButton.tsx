import { useRef } from "react";
import { label, LABELS } from "../../lib/labels";
import { useUiStore } from "../../lib/store";

type Props = {
  disabled?: boolean;
  onPushStart: () => void;
  onPushEnd: () => void;
};

const STATE_COPY: Record<string, string> = {
  idle: "Ready",
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Speaking…",
  error: "Mic error",
};

export function MicButton({ disabled, onPushStart, onPushEnd }: Props) {
  const showZh = useUiStore((s) => s.showZhLabels);
  const micState = useUiStore((s) => s.micState);
  const pressed = useRef(false);

  const active = micState === "listening";

  return (
    <div className="flex flex-col items-center gap-2 py-3">
      <button
        type="button"
        disabled={disabled || micState === "thinking" || micState === "speaking"}
        aria-label={label(LABELS.mic, showZh)}
        className={`relative flex h-24 w-24 items-center justify-center rounded-full border-4 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion disabled:opacity-50 ${
          active
            ? "border-vermilion bg-vermilion/20 scale-105"
            : "border-jade/50 bg-jade/10 hover:bg-jade/20"
        }`}
        onPointerDown={(e) => {
          e.preventDefault();
          pressed.current = true;
          (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
          onPushStart();
        }}
        onPointerUp={() => {
          if (!pressed.current) return;
          pressed.current = false;
          onPushEnd();
        }}
        onPointerCancel={() => {
          if (!pressed.current) return;
          pressed.current = false;
          onPushEnd();
        }}
      >
        <MicIcon />
        {active ? (
          <span className="absolute inset-0 animate-ping rounded-full border-2 border-vermilion/40" />
        ) : null}
      </button>
      <p className="text-sm text-muted">{STATE_COPY[micState] ?? "Ready"}</p>
      <p className="text-xs text-muted">{label(LABELS.micTap, showZh)}</p>
    </div>
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
