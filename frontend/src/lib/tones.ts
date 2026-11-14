/** Tone colours + underline styles (colour-blind safe). */

export type Tone = 1 | 2 | 3 | 4 | 5;

export function toneOfPinyin(syllable: string): Tone {
  for (const ch of syllable) {
    if ("āēīōūǖĀĒĪŌŪǕ".includes(ch)) return 1;
    if ("áéíóúǘÁÉÍÓÚǗ".includes(ch)) return 2;
    if ("ǎěǐǒǔǚǍĚǏǑǓǙ".includes(ch)) return 3;
    if ("àèìòùǜÀÈÌÒÙǛ".includes(ch)) return 4;
  }
  return 5;
}

export const TONE_CLASS: Record<Tone, string> = {
  1: "text-[#C8372D] underline decoration-solid decoration-1",
  2: "text-[#D97706] underline decoration-double decoration-1",
  3: "text-[#3F7D6B] underline decoration-dotted decoration-2",
  4: "text-[#2563EB] underline decoration-wavy decoration-1",
  5: "text-muted underline decoration-dashed decoration-1",
};
