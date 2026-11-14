import { FormEvent, useState } from "react";
import type { Message, Token } from "../../lib/api";
import { CorrectionCard } from "./CorrectionCard";
import { RubyText } from "./RubyText";

type Props = {
  messages: Message[];
  showPinyin: boolean;
  showHanzi: boolean;
  showEnglish: boolean;
  busy: boolean;
  onSend: (text: string) => Promise<void>;
  onSelectToken: (token: Token, message: Message) => void;
  activeToken: Token | null;
};

export function ChatPanel({
  messages,
  showPinyin,
  showHanzi,
  showEnglish,
  busy,
  onSend,
  onSelectToken,
  activeToken,
}: Props) {
  const [draft, setDraft] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    await onSend(text);
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6 md:px-8">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <h1 className="font-serif text-3xl text-ink">准备好了再说</h1>
            <p className="max-w-md text-muted">选好话题和等级，用中文打一句试试。</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`max-w-2xl ${msg.role === "user" ? "ml-auto text-right" : ""}`}
            >
              <div
                className={`inline-block rounded-lg px-4 py-3 text-left ${
                  msg.role === "user" ? "bg-jade/10" : "bg-ink/5"
                }`}
              >
                {msg.tokens && msg.tokens.length > 0 ? (
                  <RubyText
                    tokens={msg.tokens}
                    showPinyin={showPinyin}
                    showHanzi={showHanzi}
                    active={activeToken}
                    onSelect={(t) => onSelectToken(t, msg)}
                  />
                ) : (
                  <p className="font-serif text-hanzi">{msg.text}</p>
                )}
                {showEnglish && msg.translation ? (
                  <p className="mt-2 text-sm text-muted">{msg.translation}</p>
                ) : null}
                {!showEnglish && msg.translation ? (
                  <button
                    type="button"
                    className="mt-2 text-xs text-jade underline"
                    onClick={(ev) => {
                      const el = ev.currentTarget.nextElementSibling;
                      if (el) el.classList.toggle("hidden");
                    }}
                  >
                    显示翻译
                  </button>
                ) : null}
                {!showEnglish && msg.translation ? (
                  <p className="mt-1 hidden text-sm text-muted">{msg.translation}</p>
                ) : null}
              </div>
              {msg.correction ? (
                <CorrectionCard
                  original={msg.text}
                  better={msg.correction.better}
                  reason={msg.correction.reason}
                />
              ) : null}
            </div>
          ))
        )}
        {busy ? <p className="text-sm text-muted">想一想…</p> : null}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-muted/30 px-4 py-3 md:px-8"
      >
        <div className="flex gap-2">
          <label className="sr-only" htmlFor="chat-input">
            Message
          </label>
          <input
            id="chat-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="用中文说一句…"
            disabled={busy}
            className="flex-1 rounded border border-muted/40 bg-paper px-3 py-2 text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion"
          />
          <button
            type="submit"
            disabled={busy || !draft.trim()}
            className="rounded bg-vermilion px-4 py-2 text-sm text-paper disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </form>
    </div>
  );
}
