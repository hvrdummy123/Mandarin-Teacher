import { create } from "zustand";
import { applyTheme, initialTheme, type Theme } from "./theme";
import type { Message, Topic } from "./api";

export type View = "chat" | "topics" | "words" | "progress";

type UiState = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  showZhLabels: boolean;
  toggleZhLabels: () => void;
  showPinyin: boolean;
  showHanzi: boolean;
  showEnglish: boolean;
  togglePinyin: () => void;
  toggleHanzi: () => void;
  toggleEnglish: () => void;
  level: number;
  tier: number;
  setLevel: (level: number) => void;
  setTier: (tier: number) => void;
  view: View;
  setView: (view: View) => void;
  sessionId: number | null;
  setSessionId: (id: number | null) => void;
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  appendMessages: (messages: Message[]) => void;
  topics: Topic[];
  setTopics: (topics: Topic[]) => void;
  topicId: string | null;
  setTopicId: (id: string | null) => void;
  micState: "idle" | "listening" | "thinking" | "speaking" | "error";
  setMicState: (s: UiState["micState"]) => void;
};

export const useUiStore = create<UiState>((set, get) => ({
  theme: initialTheme(),
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  toggleTheme: () => {
    const next = get().theme === "light" ? "dark" : "light";
    applyTheme(next);
    set({ theme: next });
  },
  showZhLabels: true,
  toggleZhLabels: () => set({ showZhLabels: !get().showZhLabels }),
  showPinyin: true,
  showHanzi: true,
  showEnglish: true,
  togglePinyin: () => set({ showPinyin: !get().showPinyin }),
  toggleHanzi: () => set({ showHanzi: !get().showHanzi }),
  toggleEnglish: () => set({ showEnglish: !get().showEnglish }),
  level: 10,
  tier: 1,
  setLevel: (level) => {
    const clamped = Math.max(1, Math.min(100, level));
    set({ level: clamped, tier: Math.floor((clamped - 1) / 10) + 1 });
  },
  setTier: (tier) => {
    const t = Math.max(1, Math.min(10, tier));
    set({ tier: t, level: (t - 1) * 10 + 1 });
  },
  view: "chat",
  setView: (view) => set({ view }),
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  messages: [],
  setMessages: (messages) => set({ messages }),
  appendMessages: (messages) => set({ messages: [...get().messages, ...messages] }),
  topics: [],
  setTopics: (topics) => set({ topics }),
  topicId: null,
  setTopicId: (id) => set({ topicId: id }),
  micState: "idle",
  setMicState: (micState) => set({ micState }),
}));
