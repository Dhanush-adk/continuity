import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReviewForm } from "../components/review-form";
import { StatusBadge } from "../components/status-badge";

afterEach(() => vi.restoreAllMocks());

describe("decision presentation", () => {
  it("renders textual ALLOW, REVIEW, and DENY badges", () => {
    render(
      <>
        <StatusBadge value="ALLOW" />
        <StatusBadge value="REVIEW" />
        <StatusBadge value="DENY" />
      </>
    );
    expect(screen.getByText("ALLOW")).toBeTruthy();
    expect(screen.getByText("REVIEW")).toBeTruthy();
    expect(screen.getByText("DENY")).toBeTruthy();
  });

  it("posts the separate human review record", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "review-1",
          decision: "APPROVE",
          reviewer_id: "procurement-director",
          reason: "Approved",
          created_at: "2026-01-01T00:00:00Z"
        }),
        { status: 201 }
      )
    );
    const onReviewed = vi.fn();
    render(<ReviewForm authorizationId="authorization-1" onReviewed={onReviewed} />);
    fireEvent.click(screen.getByText("APPROVE"));
    await waitFor(() => expect(onReviewed).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/authorizations/authorization-1/review"),
      expect.objectContaining({ method: "POST" })
    );
  });
});
