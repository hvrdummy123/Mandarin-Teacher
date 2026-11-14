import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { Shell } from "../../src/components/Shell";

vi.mock("../../src/lib/api", () => ({
  api: {
    topics: vi.fn().mockResolvedValue([
      {
        id: "introduce",
        title_en: "Introducing yourself",
        title_zh: "自我介绍",
        ai_role: "classmate",
        scenario: "meeting",
        user_goal: "introduce",
        keywords: ["名字"],
        min_level: 1,
      },
    ]),
    createSession: vi.fn(),
    sendMessage: vi.fn(),
    saveWord: vi.fn(),
    listWords: vi.fn().mockResolvedValue([]),
  },
}));

describe("Shell", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("shows brand and transcript toggles", async () => {
    const user = userEvent.setup();
    render(<Shell />);
    expect(screen.getAllByText("对话").length).toBeGreaterThan(0);
    expect(screen.getByText(/准备好了再说/)).toBeInTheDocument();
    const pinyin = screen.getByRole("button", { name: "拼音" });
    await user.click(pinyin);
    expect(pinyin).toHaveAttribute("aria-pressed", "false");
  });
});
