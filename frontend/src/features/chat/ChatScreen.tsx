import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, type Message, type Token } from "../../lib/api";
import { label, LABELS } from "../../lib/labels";
import { playTts } from "../../lib/playTts";
import { useUiStore } from "../../lib/store";
import { MicButton } from "../voice/MicButton";
import { useVoiceTurn, type LiveDraft } from "../voice/useVoiceTurn";
import { CorrectionCard } from "./CorrectionCard";
import { StackedTranscript } from "./StackedTranscript";

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
  const patchMessage = useUiStore((s) => s.patchMessage);
  const topicId = useUiStore((s) => s.topicId);
  const setMicState = useUiStore((s) => s.setMicState);
  const reviewBeforeSend = useUiStore((s) => s.reviewBeforeSend);
  const toggleReviewBeforeSend = useUiStore((s) => s.toggleReviewBeforeSend);

  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [liveDraft, setLiveDraft] = useState<LiveDraft | null>(null);
  const [pendingReview, setPendingReview] = useState<LiveDraft | null>(null);

  useEffect(() => {
    const applyReview = (detail: LiveDraft) => {
      if (!detail?.text) return;
      setPendingReview(detail);
      setLiveDraft(null);
      setMicState("listening");
    };
    const onDemoReview = (ev: Event) => {
      applyReview((ev as CustomEvent<LiveDraft>).detail);
    };
    window.addEventListener("duihua:demo-review", onDemoReview);
    (
      window as Window & { __DUIHUA_SET_REVIEW__?: (d: LiveDraft) => void }
    ).__DUIHUA_SET_REVIEW__ = applyReview;
    return () => {
      window.removeEventListener("duihua:demo-review", onDemoReview);
      delete (window as Window & { __DUIHUA_SET_REVIEW__?: (d: LiveDraft) => void })
        .__DUIHUA_SET_REVIEW__;
    };
  }, [setMicState]);

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
    setNotice(null);
    setMicState("thinking");
    try {
      const sid = await ensureFreeSession();
      const turn = await api.sendMessage(sid, text);
      appendMessages([turn.user_message, turn.assistant_message]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Send failed";
      setError(msg);
      setMicState("idle");
    } finally {
      setBusy(false);
      setMicState("idle");
    }
  };

  const voice = useVoiceTurn({
    getSessionId: ensureFreeSession,
    onUserMessage: (msg) => appendMessages([msg]),
    onAssistantMessage: (msg) => appendMessages([msg]),
    onPatchMessage: (msg) => patchMessage(msg.id, msg),
    onLiveDraft: setLiveDraft,
    onReviewPending: (text) => {
      setLiveDraft(null);
      const raw = (text || "").trim();
      setPendingReview({
        text: raw,
        tokens: null,
        translation: null,
        pinyinLine: null,
      });
      if (!raw) return;
      void api
        .enrich(raw, { topic_id: topicId, repair: true })
        .then((enriched) => {
          setPendingReview({
            text: enriched.text,
            tokens: enriched.tokens,
            translation: enriched.translation_en,
            pinyinLine: enriched.pinyin_line,
            originalText: enriched.original_text,
            repairNote: enriched.repair_note,
          });
        })
        .catch(() => undefined);
    },
    onNotice: (msg) => {
      setNotice(msg);
      setError(null);
      setMicState("idle");
    },
    onError: (msg) => {
      setError(msg);
      setMicState("idle");
    },
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    await onSendText(text);
  }

  async function confirmPending() {
    const text = (pendingReview?.text || "").trim();
    if (!text || busy) return;
    setPendingReview(null);
    await onSendText(text);
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6 md:px-8">
        {messages.length === 0 && !liveDraft && !pendingReview ? (
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

        {liveDraft ? (
          <div className="ml-auto max-w-2xl text-right">
            <div className="inline-block rounded-2xl bg-jade px-4 py-3 text-left text-paper shadow-sm">
              <StackedTranscript
                live
                text={liveDraft.text || "…"}
                tokens={liveDraft.tokens}
                translation={liveDraft.translation}
                showPinyin={showPinyin}
                showHanzi={showHanzi}
                showEnglish={showEnglish}
              />
            </div>
            <p className="mt-1 text-xs text-muted">Speaking…</p>
          </div>
        ) : null}

        {pendingReview !== null ? (
          <div className="ml-auto max-w-2xl text-right">
            <p className="mb-1 text-xs text-muted">{label(LABELS.pendingReview, showZh)}</p>
            <div className="inline-block rounded-2xl border-2 border-dashed border-jade/50 bg-jade/10 px-4 py-3 text-left">
              {pendingReview.repairNote ? (
                <p className="mb-2 text-xs text-jade">{pendingReview.repairNote}</p>
              ) : null}
              {pendingReview.originalText ? (
                <p className="mb-1 text-xs text-muted line-through">{pendingReview.originalText}</p>
              ) : null}
              <StackedTranscript
                text={pendingReview.text || "(nothing heard)"}
                tokens={pendingReview.tokens}
                translation={pendingReview.translation}
                showPinyin={showPinyin}
                showHanzi={showHanzi}
                showEnglish={showEnglish}
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy || !pendingReview.text.trim()}
                  className="rounded bg-jade px-3 py-1.5 text-sm text-paper disabled:opacity-50"
                  onClick={() => void confirmPending()}
                >
                  {label(LABELS.confirmSend, showZh)}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className="rounded border border-muted/40 px-3 py-1.5 text-sm text-muted"
                  onClick={() => {
                    setPendingReview(null);
                    void voice.start();
                  }}
                >
                  {label(LABELS.discard, showZh)}
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {busy ? <p className="text-sm text-muted">{label(LABELS.thinking, showZh)}</p> : null}
        {notice ? (
          <p className="text-sm text-jade" role="status">
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="text-sm text-vermilion" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="border-t border-muted/30 px-4 pb-4 pt-2 md:px-8">
        <label className="mb-2 flex cursor-pointer items-start gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="mt-1"
            checked={reviewBeforeSend}
            onChange={() => toggleReviewBeforeSend()}
          />
          <span>
            <span className="font-medium">{label(LABELS.reviewBeforeSend, showZh)}</span>
            <span className="mt-0.5 block text-xs text-muted">{LABELS.reviewHint.en}</span>
          </span>
        </label>

        <MicButton
          disabled={busy || pendingReview !== null}
          onToggle={() => void voice.toggle()}
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
            setLiveDraft(null);
            setPendingReview(null);
            setError(null);
            setNotice(null);
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
  const isUser = msg.role === "user";
  const [playing, setPlaying] = useState(false);

  return (
    <div className={`max-w-2xl ${isUser ? "ml-auto text-right" : ""}`}>
      <div
        className={`inline-block rounded-2xl px-4 py-3 text-left shadow-sm ${
          isUser ? "bg-jade text-paper" : "bg-ink/5 text-ink"
        }`}
      >
        {msg.heard_raw && msg.heard_raw !== msg.text ? (
          <p className={`mb-1 text-xs ${isUser ? "text-paper/70" : "text-muted"}`}>
            {label(LABELS.heard, showZh)}: {msg.heard_raw}
          </p>
        ) : null}
        <div className={isUser ? "[&_.text-muted]:text-paper/80 [&_.text-ink]:text-paper" : ""}>
          <StackedTranscript
            text={msg.text}
            tokens={msg.tokens}
            translation={msg.translation}
            showPinyin={showPinyin}
            showHanzi={showHanzi}
            showEnglish={showEnglish}
            activeToken={activeToken}
            onSelectToken={(t) => onSelectToken(t, msg)}
          />
        </div>
        <button
          type="button"
          disabled={playing || !msg.text.trim()}
          title={label(LABELS.playMessage, showZh)}
          aria-label={label(LABELS.playMessage, showZh)}
          className={`mt-2 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs ${
            isUser
              ? "bg-paper/20 text-paper hover:bg-paper/30"
              : "bg-jade/15 text-jade hover:bg-jade/25"
          } disabled:opacity-50`}
          onClick={() => {
            setPlaying(true);
            void playTts(msg.text).finally(() => setPlaying(false));
          }}
        >
          <SpeakerIcon />
          {playing ? "…" : label(LABELS.playMessage, showZh)}
        </button>
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

function SpeakerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M11 5 6 9H3v6h3l5 4V5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M15.5 8.5a5 5 0 0 1 0 7M18.5 6a9 9 0 0 1 0 12"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
