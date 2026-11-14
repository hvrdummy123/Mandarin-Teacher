/** Live interim transcripts via the browser SpeechRecognition API (zh-CN). */

export type SpeechHandlers = {
  onPartial: (text: string, isFinal: boolean) => void;
  onError?: (msg: string) => void;
};

type Recog = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((ev: SpeechResultEvent) => void) | null;
  onerror: ((ev: { error: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechResultEvent = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

function getRecognitionCtor(): (new () => Recog) | null {
  const w = window as unknown as {
    SpeechRecognition?: new () => Recog;
    webkitSpeechRecognition?: new () => Recog;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function browserSpeechSupported(): boolean {
  return getRecognitionCtor() != null;
}

/** Start continuous zh-CN recognition; returns a stop function. */
export function startBrowserSpeech(handlers: SpeechHandlers): () => void {
  const Ctor = getRecognitionCtor();
  if (!Ctor) {
    handlers.onError?.("Live captions need Chrome/Edge (SpeechRecognition). Final STT still uses Whisper.");
    return () => undefined;
  }

  const recog = new Ctor();
  recog.lang = "zh-CN";
  recog.continuous = true;
  recog.interimResults = true;

  let stopped = false;
  let committed = "";

  recog.onresult = (ev) => {
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const piece = ev.results[i]![0]!.transcript;
      if (ev.results[i]!.isFinal) {
        committed = `${committed}${piece}`.trim();
        handlers.onPartial(committed, true);
      } else {
        interim += piece;
      }
    }
    const live = `${committed} ${interim}`.trim();
    if (live) handlers.onPartial(live, false);
  };

  recog.onerror = (ev) => {
    // "no-speech" / "aborted" are normal when toggling the mic.
    if (ev.error === "no-speech" || ev.error === "aborted") return;
    handlers.onError?.(ev.error);
  };

  recog.onend = () => {
    // Chrome stops after pauses; restart while still listening.
    if (!stopped) {
      try {
        recog.start();
      } catch {
        /* already started */
      }
    }
  };

  try {
    recog.start();
  } catch (err) {
    handlers.onError?.(err instanceof Error ? err.message : "SpeechRecognition failed");
  }

  return () => {
    stopped = true;
    try {
      recog.onend = null;
      recog.stop();
    } catch {
      try {
        recog.abort();
      } catch {
        /* ignore */
      }
    }
  };
}
