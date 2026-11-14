import { create } from "zustand";
import { applyTheme, initialTheme, type Theme } from "./theme";
import type { Message, Topic } from "./api";

type UiState = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  showPinyin: boolean;
  showHanzi: boolean;
  showEnglish: boolean;
  togglePinyin: () => void;
  toggleHanzi: () => void;
  toggleEnglish: () => void;
  level: number;
  tier: number;
  topicId: string | null;
  setLevel: (level: number) => void;
  setTier: (tier: number) => void;
  setTopicId: (id: string | null) => void;
  sessionId: number | null;
  setSessionId: (id: number | null) => void;
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  appendMessages: (messages: Message[]) => void;
  topics: Topic[];
  setTopics: (topics: Topic[]) => void;
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
  showPinyin: true,
  showHanzi: true,
  showEnglish: false,
  togglePinyin: () => set({ showPinyin: !get().showPinyin }),
  toggleHanzi: () => set({ showHanzi: !get().showHanzi }),
  toggleEnglish: () => set({ showEnglish: !get().showEnglish }),
  level: 10,
  tier: 1,
  topicId: "introduce",
  setLevel: (level) => {
    const clamped = Math.max(1, Math.min(100, level));
    set({ level: clamped, tier: Math.floor((clamped - 1) / 10) + 1 });
  },
  setTier: (tier) => {
    const t = Math.max(1, Math.min(10, tier));
    set({ tier: t, level: (t - 1) * 10 + 1 });
  },
  setTopicId: (id) => set({ topicId: id }),
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  messages: [],
  setMessages: (messages) => set({ messages }),
  appendMessages: (messages) => set({ messages: [...get().messages, ...messages] }),
  topics: [],
  setTopics: (topics) => set({ topics }),
}));
