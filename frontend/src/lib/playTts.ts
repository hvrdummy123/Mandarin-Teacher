/** Play text with the same Edge TTS voice used for AI replies. */

let current: HTMLAudioElement | null = null;

export async function playTts(text: string): Promise<void> {
  const trimmed = text.trim();
  if (!trimmed) return;

  if (current) {
    current.pause();
    current = null;
  }

  const res = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: trimmed }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  current = audio;
  await new Promise<void>((resolve, reject) => {
    audio.onended = () => {
      URL.revokeObjectURL(url);
      if (current === audio) current = null;
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      if (current === audio) current = null;
      reject(new Error("Audio playback failed"));
    };
    void audio.play().catch(reject);
  });
}

export function stopTts(): void {
  if (current) {
    current.pause();
    current = null;
  }
}
