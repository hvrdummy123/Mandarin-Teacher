import { FormEvent, useCallback, useState } from "react";
import { api, type Message, type Token } from "../../lib/api";
import { label, LABELS } from "../../lib/labels";
import { useUiStore } from "../../lib/store";
import { MicButton } from "../voice/MicButton";
import { useVoiceTurn } from "../voice/useVoiceTurn";
import { CorrectionCard } from "./CorrectionCard";
import { RubyText } from "./RubyText";

type Props = {
  onSelectToken: (token: Token, message: Message) => void;
  activeToken: Token | null;
};

export function ChatScreen({ onSelectToken, activeToken }: Props) {
  const showZh = useUiStore((s) => s.showZhLabels);
  const showPinyin = useUiStore((s) => s.showPinyin);
  const showHanzi = useUiStore((s) => s.showHanzi);
  const showEnglish = useUiStore((s) => s.showEnglish);
  const level = useUiStore((s) => s.level);
  const sessionId = useUiStore((s) => s.sessionId);
  const setSessionId = useUiStore((s) => s.setSessionId);
  const messages = useUiStore((s) => s.messages);
  const setMessages = useUiStore((s) => s.setMessages);
  const appendMessages = useUiStore((s) => s.appendMessages);
  const topicId = useUiStore((s) => s.topicId);
  const setMicState = useUiStore((s) => s.setMicState);

  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ensureFreeSession = useCallback(async () => {
    if (sessionId != null) return sessionId;
    const session = await api.createSession({
      mode: "free",
      topic_id: null,
      level,
    });
    setSessionId(session.id);
    return session.id;
  }, [sessionId, level, setSessionId]);

  const onSendText = async (text: string) => {
    setBusy(true);
    setError(null);
    setMicState("thinking");
    try {
      const sid = await ensureFreeSession();
      const turn = await api.sendMessage(sid, text);
      appendMessages([turn.user_message, turn.assistant_message]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
      setMicState("error");
    } finally {
      setBusy(false);
      setMicState("idle");
    }
  };

  const voice = useVoiceTurn({
    getSessionId: ensureFreeSession,
    onUserMessage: (msg) => appendMessages([msg]),
    onAssistantMessage: (msg) => appendMessages([msg]),
    onError: (msg) => {
      setError(msg);
      setMicState("error");
    },
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    await onSendText(text);
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6 md:px-8">
        {messages.length === 0 ? (
          <div className="mx-auto max-w-md space-y-2 text-center">
            <h1 className="font-serif text-3xl text-ink">{label(LABELS.chat, showZh)}</h1>
            <p className="text-muted">{LABELS.chatEmpty.en}</p>
            {showZh ? <p className="text-xs text-muted">{LABELS.chatEmpty.zh}</p> : null}
            {topicId ? (
              <p className="text-xs text-muted">
                Topic session active. Switch to Topics to start a new role-play.
              </p>
            ) : null}
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              showPinyin={showPinyin}
              showHanzi={showHanzi}
              showEnglish={showEnglish}
              showZh={showZh}
              activeToken={activeToken}
              onSelectToken={onSelectToken}
            />
          ))
        )}
        {busy ? <p className="text-sm text-muted">{label(LABELS.thinking, showZh)}</p> : null}
        {error ? (
          <p className="text-sm text-vermilion" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="border-t border-muted/30 px-4 pb-4 pt-2 md:px-8">
        <MicButton
          disabled={busy}
          onPushStart={() => void voice.start()}
          onPushEnd={() => void voice.stop()}
        />
        <form onSubmit={handleSubmit} className="mt-1">
          <label className="sr-only" htmlFor="chat-fallback">
            Text fallback
          </label>
          <div className="flex gap-2">
            <input
              id="chat-fallback"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={label(LABELS.typeFallback, showZh)}
              disabled={busy}
              className="flex-1 rounded border border-muted/30 bg-paper/80 px-3 py-1.5 text-sm text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-vermilion"
            />
            <button
              type="submit"
              disabled={busy || !draft.trim()}
              className="rounded border border-muted/40 px-3 py-1.5 text-sm text-muted disabled:opacity-50"
            >
              {label(LABELS.send, showZh)}
            </button>
          </div>
        </form>
        <button
          type="button"
          className="mt-2 text-xs text-muted underline"
          onClick={() => {
            setMessages([]);
            setSessionId(null);
          }}
        >
          New free chat
        </button>
      </div>
    </div>
  );
}

function MessageBubble({
  msg,
  showPinyin,
  showHanzi,
  showEnglish,
  showZh,
  activeToken,
  onSelectToken,
}: {
  msg: Message;
  showPinyin: boolean;
  showHanzi: boolean;
  showEnglish: boolean;
  showZh: boolean;
  activeToken: Token | null;
  onSelectToken: (token: Token, message: Message) => void;
}) {
  return (
    <div className={`max-w-2xl ${msg.role === "user" ? "ml-auto text-right" : ""}`}>
      <div
        className={`inline-block rounded-lg px-4 py-3 text-left ${
          msg.role === "user" ? "bg-jade/10" : "bg-ink/5"
        }`}
      >
        {msg.heard_raw && msg.heard_raw !== msg.text ? (
          <p className="mb-1 text-xs text-muted">
            {label(LABELS.heard, showZh)}: {msg.heard_raw}
          </p>
        ) : null}
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
      </div>
      {msg.correction ? (
        <CorrectionCard
          original={msg.text}
          better={msg.correction.better}
          reason={msg.correction.reason}
        />
      ) : null}
    </div>
  );
}
