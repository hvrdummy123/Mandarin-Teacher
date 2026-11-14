import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
    openTopic: vi.fn(),
    sendMessage: vi.fn(),
    saveWord: vi.fn(),
    listWords: vi.fn().mockResolvedValue([]),
    deleteWord: vi.fn(),
    progress: vi.fn().mockResolvedValue({
      xp_today: 0,
      daily_goal: 100,
      streak: 0,
      level: 10,
      tier: 1,
      note: "stub",
    }),
  },
}));

vi.mock("../../src/features/voice/useVoiceTurn", () => ({
  useVoiceTurn: () => ({
    start: vi.fn(),
    stop: vi.fn(),
    toggle: vi.fn(),
    isSupportedLive: false,
  }),
}));

describe("Shell", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("shows English rail labels and distinct screens", async () => {
    const user = userEvent.setup();
    render(<Shell />);
    expect(screen.getAllByRole("button", { name: /Chat/ }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /Topics/ }).length).toBeGreaterThan(0);
    expect(screen.getByText(/Free conversation at your level/)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /Topics/ })[0]!);
    expect(await screen.findByText(/Pick a scenario/)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /Progress/ })[0]!);
    expect(await screen.findByText(/XP today/)).toBeInTheDocument();
  });
});
