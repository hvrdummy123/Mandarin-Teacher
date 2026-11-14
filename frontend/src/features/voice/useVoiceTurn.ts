import { useCallback, useEffect, useRef } from "react";
import type { Message, Token } from "../../lib/api";
import { api } from "../../lib/api";
import { useUiStore } from "../../lib/store";
import { browserSpeechSupported, startBrowserSpeech } from "./useBrowserSpeech";

export type LiveDraft = {
  text: string;
  tokens: Token[] | null;
  translation: string | null;
  pinyinLine: string | null;
  originalText?: string | null;
  repairNote?: string | null;
};

type Handlers = {
  getSessionId: () => Promise<number>;
  onUserMessage: (msg: Message) => void;
  onAssistantMessage: (msg: Message) => void;
  onPatchMessage: (msg: Message) => void;
  onLiveDraft: (draft: LiveDraft | null) => void;
  onReviewPending: (text: string) => void;
  onNotice: (msg: string) => void;
  onError: (msg: string) => void;
  onListeningEnded?: () => void;
};

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/voice`;
}

function isRateLimitMsg(msg: string): boolean {
  return /429|rate-limited|rate limited|providers available/i.test(msg);
}

export function useVoiceTurn(handlers: Handlers) {
  const setMicState = useUiStore((s) => s.setMicState);
  const level = useUiStore((s) => s.level);
  const handlersRef = useRef(handlers);
  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  const wsRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const workletRef = useRef<AudioWorkletNode | null>(null);
  const stopSpeechRef = useRef<(() => void) | null>(null);
  const enrichTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastEnrichText = useRef("");
  const liveTextRef = useRef("");
  const playChain = useRef<Promise<void>>(Promise.resolve());
  const activeRef = useRef(false);

  const cleanupCapture = useCallback(async () => {
    stopSpeechRef.current?.();
    stopSpeechRef.current = null;
    if (enrichTimer.current) {
      clearTimeout(enrichTimer.current);
      enrichTimer.current = null;
    }
    workletRef.current?.port.close();
    workletRef.current?.disconnect();
    workletRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (ctxRef.current) {
      await ctxRef.current.close().catch(() => undefined);
      ctxRef.current = null;
    }
  }, []);

  const scheduleEnrich = useCallback((text: string) => {
    liveTextRef.current = text;
    handlersRef.current.onLiveDraft({
      text,
      tokens: null,
      translation: null,
      pinyinLine: null,
    });
    if (enrichTimer.current) clearTimeout(enrichTimer.current);
    enrichTimer.current = setTimeout(() => {
      void (async () => {
        const trimmed = text.trim();
        if (!trimmed || trimmed === lastEnrichText.current) return;
        lastEnrichText.current = trimmed;
        try {
          const topicId = useUiStore.getState().topicId;
          const enriched = await api.enrich(trimmed, { topic_id: topicId, repair: true });
          // Keep live caption as heard; repaired text is applied on review/send.
          handlersRef.current.onLiveDraft({
            text: enriched.text,
            tokens: enriched.tokens as Token[],
            translation: enriched.translation_en,
            pinyinLine: enriched.pinyin_line,
            originalText: enriched.original_text,
            repairNote: enriched.repair_note,
          });
          if (enriched.repaired) liveTextRef.current = enriched.text;
        } catch {
          /* keep raw live text */
        }
      })();
    }, 280);
  }, []);

  const enqueueAudio = useCallback(
    (data: ArrayBuffer) => {
      const blob = new Blob([data], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      playChain.current = playChain.current.then(
        () =>
          new Promise<void>((resolve) => {
            const audio = new Audio(url);
            setMicState("speaking");
            audio.onended = () => {
              URL.revokeObjectURL(url);
              resolve();
            };
            audio.onerror = () => {
              URL.revokeObjectURL(url);
              resolve();
            };
            void audio.play().catch(() => resolve());
          }),
      );
      void playChain.current.then(() => {
        if (!activeRef.current) setMicState("idle");
      });
    },
    [setMicState],
  );

  const start = useCallback(async () => {
    if (activeRef.current) return;
    activeRef.current = true;
    lastEnrichText.current = "";
    liveTextRef.current = "";
    const h = handlersRef.current;
    try {
      setMicState("listening");
      h.onLiveDraft({ text: "", tokens: null, translation: null, pinyinLine: null });

      const sessionId = await h.getSessionId();
      const ws = new WebSocket(wsUrl());
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error("WebSocket failed — is the API running on :8000?"));
        setTimeout(() => reject(new Error("WebSocket timeout")), 8000);
      });

      ws.send(
        JSON.stringify({
          type: "session.start",
          session_id: sessionId,
          level,
        }),
      );
      ws.send(JSON.stringify({ type: "turn.start", hands_free: false }));

      ws.onmessage = (ev) => {
        if (typeof ev.data !== "string") {
          enqueueAudio(ev.data as ArrayBuffer);
          return;
        }
        const msg = JSON.parse(ev.data) as {
          type: string;
          message?: Message;
          detail?: string;
          user_message?: Message;
          assistant_message?: Message;
        };
        if (msg.type === "transcript.user" && msg.message) {
          handlersRef.current.onLiveDraft(null);
          handlersRef.current.onUserMessage(msg.message);
          setMicState("thinking");
        } else if (msg.type === "reply.sentence" && msg.message) {
          handlersRef.current.onAssistantMessage(msg.message);
        } else if (msg.type === "analysis") {
          if (msg.user_message) handlersRef.current.onPatchMessage(msg.user_message);
          if (msg.assistant_message) handlersRef.current.onPatchMessage(msg.assistant_message);
        } else if (msg.type === "notice" && msg.detail) {
          handlersRef.current.onNotice(msg.detail);
          setMicState("idle");
        } else if (msg.type === "error") {
          handlersRef.current.onLiveDraft(null);
          const detail = msg.detail || "Voice error";
          handlersRef.current.onError(detail);
          // Rate limits / soft TTS errors should not lock the mic.
          if (isRateLimitMsg(detail) || detail.includes("Hear this") || detail.includes("AI unavailable")) {
            setMicState("idle");
            activeRef.current = false;
          } else {
            setMicState("error");
            activeRef.current = false;
          }
        } else if (msg.type === "turn.end" || msg.type === "vad.end") {
          handlersRef.current.onLiveDraft(null);
          activeRef.current = false;
          setMicState("idle");
        }
      };

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;
      const ctx = new AudioContext();
      ctxRef.current = ctx;
      if (ctx.state === "suspended") await ctx.resume();
      await ctx.audioWorklet.addModule("/pcm-worklet.js");
      const source = ctx.createMediaStreamSource(stream);
      const worklet = new AudioWorkletNode(ctx, "pcm-capture");
      workletRef.current = worklet;
      worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(e.data);
      };
      source.connect(worklet);

      if (browserSpeechSupported()) {
        stopSpeechRef.current = startBrowserSpeech({
          onPartial: (text) => scheduleEnrich(text),
          onError: () => undefined,
        });
      } else {
        h.onLiveDraft({
          text: "(Listening… live captions need Chrome/Edge)",
          tokens: null,
          translation: null,
          pinyinLine: null,
        });
      }
    } catch (err) {
      activeRef.current = false;
      await cleanupCapture();
      wsRef.current?.close();
      wsRef.current = null;
      h.onLiveDraft(null);
      const detail =
        err instanceof Error
          ? err.message
          : "Microphone permission denied. Allow mic access, or type below.";
      h.onError(detail);
      setMicState("error");
    }
  }, [cleanupCapture, enqueueAudio, level, scheduleEnrich, setMicState]);

  const stop = useCallback(async () => {
    if (!activeRef.current) return;
    activeRef.current = false;
    stopSpeechRef.current?.();
    stopSpeechRef.current = null;
    const hint = liveTextRef.current.trim();
    const review = useUiStore.getState().reviewBeforeSend;
    const ws = wsRef.current;

    if (review) {
      // Abort server turn — user will confirm or discard the transcript first.
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.close();
        } catch {
          /* ignore */
        }
      }
      wsRef.current = null;
      await cleanupCapture();
      handlersRef.current.onLiveDraft(null);
      handlersRef.current.onReviewPending(hint);
      setMicState("idle");
      handlersRef.current.onListeningEnded?.();
      return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "turn.end",
          heard_hint: hint || undefined,
        }),
      );
    }
    await cleanupCapture();
    setMicState("thinking");
    handlersRef.current.onListeningEnded?.();
  }, [cleanupCapture, setMicState]);

  const toggle = useCallback(async () => {
    if (activeRef.current) await stop();
    else await start();
  }, [start, stop]);

  return { start, stop, toggle, isSupportedLive: browserSpeechSupported() };
}
