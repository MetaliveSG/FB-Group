import { describe, it, expect } from "vitest";
import { OPPORTUNITY_STAGES } from "@fbgroup/api-client";

describe("OPPORTUNITY_STAGES", () => {
  it("defines the 6 pipeline stages in board order", () => {
    expect(OPPORTUNITY_STAGES).toEqual([
      "prospecting",
      "qualified",
      "proposal",
      "negotiation",
      "won",
      "lost",
    ]);
  });

  it("ends with the two terminal stages", () => {
    const last2 = OPPORTUNITY_STAGES.slice(-2);
    expect(last2).toEqual(["won", "lost"]);
  });

  it("has no duplicate stages", () => {
    expect(new Set(OPPORTUNITY_STAGES).size).toBe(OPPORTUNITY_STAGES.length);
  });
});
