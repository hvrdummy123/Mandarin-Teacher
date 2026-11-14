import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Shell } from "../../src/components/Shell";

describe("Shell", () => {
  it("shows the brand and calm empty state", () => {
    render(<Shell />);
    expect(screen.getAllByText("对话").length).toBeGreaterThan(0);
    expect(screen.getByText(/准备好了再说/)).toBeInTheDocument();
  });
});
