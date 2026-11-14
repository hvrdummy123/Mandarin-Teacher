import { useCallback, useRef } from "react";
import type { Message } from "../../lib/api";
import { useUiStore } from "../../lib/store";

type Handlers = {
  getSessionId: () => Promise<number>;
  onUserMessage: (msg: Message) => void;
  onAssistantMessage: (msg: Message) => void;
  onError: (msg: string) => void;
};

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.host;
  return `${proto}://${host}/ws/voice`;
}

export function useVoiceTurn(handlers: Handlers) {
  const setMicState = useUiStore((s) => s.setMicState);
  const level = useUiStore((s) => s.level);
  const wsRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const workletRef = useRef<AudioWorkletNode | null>(null);
  const audioQueue = useRef<HTMLAudioElement[]>([]);

  const cleanupCapture = useCallback(async () => {
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

  const start = useCallback(async () => {
    try {
      setMicState("listening");
      const sessionId = await handlers.getSessionId();
      const ws = new WebSocket(wsUrl());
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error("WebSocket failed to open"));
      });

      ws.send(
        JSON.stringify({
          type: "session.start",
          session_id: sessionId,
          level,
        }),
      );
      ws.send(JSON.stringify({ type: "turn.start" }));

      ws.onmessage = (ev) => {
        if (typeof ev.data !== "string") {
          // MP3/audio down
          const blob = new Blob([ev.data], { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audioQueue.current.push(audio);
          setMicState("speaking");
          void audio.play().finally(() => {
            URL.revokeObjectURL(url);
            audioQueue.current = audioQueue.current.filter((a) => a !== audio);
            if (audioQueue.current.length === 0) setMicState("idle");
          });
          return;
        }
        const msg = JSON.parse(ev.data) as {
          type: string;
          message?: Message;
          detail?: string;
        };
        if (msg.type === "transcript.user" && msg.message) {
          handlers.onUserMessage(msg.message);
          setMicState("thinking");
        } else if (msg.type === "reply.sentence" && msg.message) {
          handlers.onAssistantMessage(msg.message);
        } else if (msg.type === "error") {
          handlers.onError(msg.detail || "Voice error");
          setMicState("error");
        } else if (msg.type === "turn.end") {
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
      await ctx.audioWorklet.addModule("/pcm-worklet.js");
      const source = ctx.createMediaStreamSource(stream);
      const worklet = new AudioWorkletNode(ctx, "pcm-capture");
      workletRef.current = worklet;
      worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(e.data);
        }
      };
      source.connect(worklet);
    } catch (err) {
      await cleanupCapture();
      const detail =
        err instanceof Error
          ? err.message
          : "Microphone permission denied. Allow mic access, or type below.";
      handlers.onError(detail);
      setMicState("error");
    }
  }, [cleanupCapture, handlers, level, setMicState]);

  const stop = useCallback(async () => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "turn.end" }));
    }
    await cleanupCapture();
    setMicState("thinking");
  }, [cleanupCapture, setMicState]);

  return { start, stop };
}
