/** English UI copy with optional Chinese secondary labels. */

export type L = { en: string; zh: string };

export const LABELS = {
  brand: { en: "duihua", zh: "对话" },
  chat: { en: "Chat", zh: "对话" },
  topics: { en: "Topics", zh: "话题" },
  words: { en: "Saved words", zh: "生词" },
  progress: { en: "Progress", zh: "进度" },
  pinyin: { en: "Pinyin", zh: "拼音" },
  hanzi: { en: "Hanzi", zh: "汉字" },
  english: { en: "English", zh: "英文" },
  dark: { en: "Dark", zh: "深色" },
  light: { en: "Light", zh: "浅色" },
  hideZh: { en: "Hide Chinese labels", zh: "隐藏中文" },
  showZh: { en: "Show Chinese labels", zh: "显示中文" },
  level: { en: "Level", zh: "等级" },
  tier: { en: "Tier", zh: "档" },
  freeChat: { en: "Free chat", zh: "自由聊天" },
  send: { en: "Send", zh: "发送" },
  thinking: { en: "Thinking…", zh: "想一想…" },
  save: { en: "Save", zh: "收藏" },
  saved: { en: "Saved", zh: "已保存" },
  close: { en: "Close", zh: "关闭" },
  play: { en: "Play", zh: "播放" },
  playWord: { en: "Hear word", zh: "听单词" },
  playSentence: { en: "Hear sentence", zh: "听整句" },
  playMessage: { en: "Hear this", zh: "听这个" },
  playCorrection: { en: "Hear correction", zh: "听正确说法" },
  search: { en: "Search", zh: "搜索" },
  delete: { en: "Delete", zh: "删除" },
  mic: { en: "Speak", zh: "说话" },
  micTap: { en: "Tap to speak", zh: "点一下开始说" },
  micDone: { en: "Tap when you're done", zh: "说完再点一下" },
  typeFallback: { en: "Or type as a fallback…", zh: "或打字…" },
  chatEmpty: {
    en: "Free conversation at your level. Tap the mic, speak Mandarin (English words OK), tap again when done.",
    zh: "点麦克风说中文（可以夹杂英文），说完再点一下。",
  },
  topicsTitle: { en: "Topics", zh: "话题" },
  topicsHint: {
    en: "Pick a scenario. The AI will open in character, in Chinese, at your level.",
    zh: "选一个场景，AI 会用角色身份先开口。",
  },
  wordsEmpty: {
    en: "No saved words yet. Tap a word in chat, then Save.",
    zh: "还没有收藏。点对话里的词再点收藏。",
  },
  progressStub: {
    en: "XP and streaks fill in during Phase 3. Numbers below are placeholders.",
    zh: "积分和连续天数会在第三阶段接上。",
  },
  suggestedLevel: { en: "Suggested level", zh: "建议等级" },
  start: { en: "Start", zh: "开始" },
  showTranslation: { en: "Show translation", zh: "显示翻译" },
  heard: { en: "Heard", zh: "听到的" },
  suggestion: { en: "I think you meant…", zh: "你是不是想说…" },
  reviewBeforeSend: { en: "Review before send", zh: "先看再发送" },
  reviewHint: {
    en: "On: check the transcript, then Send or Discard. Off: send as soon as you finish speaking.",
    zh: "开：先看识别结果再发送或重录。关：说完立刻发送。",
  },
  confirmSend: { en: "Send", zh: "发送" },
  discard: { en: "Discard", zh: "重录" },
  pendingReview: { en: "Check this before sending", zh: "发送前请确认" },
} as const;

export function label(item: L, showZh: boolean): string {
  return showZh ? `${item.en} · ${item.zh}` : item.en;
}
