const API = "";

export type Token = {
  surface: string;
  pinyin: string;
  definitions: string[];
  hsk: number | null;
  chars: { ch: string; pinyin: string; meaning: string }[];
  out_of_level?: boolean;
};

export type Message = {
  id: number;
  session_id: number;
  role: string;
  text: string;
  tokens: Token[] | null;
  translation: string | null;
  correction: { better: string; reason: string } | null;
  created_at: string | null;
  audio_path?: string | null;
  heard_raw?: string | null;
};

export type Topic = {
  id: string;
  title_en: string;
  title_zh: string;
  ai_role: string;
  scenario: string;
  user_goal: string;
  keywords: string[];
  min_level: number;
};

export type Session = {
  id: number;
  mode: string;
  topic_id: string | null;
  level: number;
};

export type Progress = {
  xp_today: number;
  daily_goal: number;
  streak: number;
  level: number;
  tier: number;
  note: string;
};

export type SavedWord = {
  id: number;
  word: string;
  pinyin: string;
  definition: string;
  hsk_level: number | null;
  context_sentence: string | null;
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  topics: () => json<Topic[]>("/api/topics"),
  createSession: (body: { mode: string; topic_id: string | null; level: number }) =>
    json<Session>("/api/sessions", { method: "POST", body: JSON.stringify(body) }),
  openTopic: (body: { topic_id: string; level: number }) =>
    json<{ session: Session; assistant_message: Message }>("/api/sessions/open-topic", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  sendMessage: (sessionId: number, text: string) =>
    json<{
      user_message: Message;
      assistant_message: Message;
      analysis: Record<string, unknown>;
      level_postcheck: { regenerated: boolean; out_of_level: string[] };
    }>(`/api/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  listMessages: (sessionId: number) => json<Message[]>(`/api/sessions/${sessionId}/messages`),
  saveWord: (body: {
    word: string;
    pinyin: string;
    definition: string;
    hsk_level: number | null;
    context_sentence: string | null;
  }) => json<SavedWord>("/api/words", { method: "POST", body: JSON.stringify(body) }),
  listWords: (q?: string) =>
    json<SavedWord[]>(`/api/words${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  deleteWord: (id: number) => json<{ status: string }>(`/api/words/${id}`, { method: "DELETE" }),
  progress: () => json<Progress>("/api/progress"),
};
