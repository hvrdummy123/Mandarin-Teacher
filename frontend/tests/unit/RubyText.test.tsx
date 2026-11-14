import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RubyText } from "../../src/features/chat/RubyText";
import type { Token } from "../../src/lib/api";
import { toneOfPinyin, TONE_CLASS } from "../../src/lib/tones";

const token: Token = {
  surface: "你好",
  pinyin: "nǐ hǎo",
  definitions: ["hello"],
  hsk: 1,
  chars: [
    { ch: "你", pinyin: "nǐ", meaning: "you" },
    { ch: "好", pinyin: "hǎo", meaning: "good" },
  ],
};

describe("tones", () => {
  it("detects tone numbers", () => {
    expect(toneOfPinyin("nǐ")).toBe(3);
    expect(toneOfPinyin("hǎo")).toBe(3);
    expect(toneOfPinyin("kā")).toBe(1);
    expect(toneOfPinyin("de")).toBe(5);
  });

  it("maps each tone to a distinct class", () => {
    const classes = [1, 2, 3, 4, 5].map((t) => TONE_CLASS[t as 1 | 2 | 3 | 4 | 5]);
    expect(new Set(classes).size).toBe(5);
  });
});

describe("RubyText", () => {
  it("renders ruby pinyin and calls onSelect", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <RubyText
        tokens={[token]}
        showPinyin
        showHanzi
        onSelect={onSelect}
      />,
    );
    expect(screen.getByText("你好")).toBeInTheDocument();
    expect(screen.getByText("nǐ hǎo")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /你好/ }));
    expect(onSelect).toHaveBeenCalled();
  });
});
