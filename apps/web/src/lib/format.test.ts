import { describe, it, expect } from "vitest";
import {
  formatSGD,
  calcCartSubtotal,
  round2,
  churnColor,
  tierColor,
  wheelTargetRotation,
  relativeTime,
  prettyStage,
} from "./format";

describe("prettyStage", () => {
  it("title-cases single words", () => {
    expect(prettyStage("prospecting")).toBe("Prospecting");
    expect(prettyStage("won")).toBe("Won");
  });

  it("title-cases snake_case stage keys", () => {
    expect(prettyStage("offer_sent")).toBe("Offer Sent");
    expect(prettyStage("at_risk")).toBe("At Risk");
    expect(prettyStage("new_customer_return")).toBe("New Customer Return");
  });
});

describe("formatSGD", () => {
  it("formats zero correctly", () => {
    expect(formatSGD(0)).toBe("S$0.00");
  });

  it("formats a whole number", () => {
    expect(formatSGD(12)).toBe("S$12.00");
  });

  it("formats a decimal amount", () => {
    expect(formatSGD(9.9)).toBe("S$9.90");
  });

  it("formats a larger amount", () => {
    expect(formatSGD(123.456)).toBe("S$123.46");
  });
});

describe("calcCartSubtotal", () => {
  it("returns 0 for empty cart", () => {
    expect(calcCartSubtotal([])).toBe(0);
  });

  it("calculates single item without modifiers", () => {
    const items = [{ unit_price: 5.5, quantity: 2, modifier_price_delta: 0 }];
    expect(calcCartSubtotal(items)).toBe(11);
  });

  it("calculates single item with modifier", () => {
    const items = [{ unit_price: 5.0, quantity: 1, modifier_price_delta: 1.5 }];
    expect(calcCartSubtotal(items)).toBe(6.5);
  });

  it("calculates multiple items", () => {
    const items = [
      { unit_price: 10.0, quantity: 2, modifier_price_delta: 0 },
      { unit_price: 4.5, quantity: 3, modifier_price_delta: 0.5 },
    ];
    // 10*2 + (4.5+0.5)*3 = 20 + 15 = 35
    expect(calcCartSubtotal(items)).toBe(35);
  });
});

describe("round2", () => {
  it("rounds to 2 decimal places", () => {
    expect(round2(1.235)).toBe(1.24);
    expect(round2(1.234)).toBe(1.23);
    expect(round2(5)).toBe(5);
    expect(round2(0.1 + 0.2)).toBe(0.3); // float drift example
  });
});

describe("churnColor", () => {
  it("returns red for high risk", () => {
    expect(churnColor("high risk")).toBe("#ef4444");
  });

  it("returns green for low risk", () => {
    expect(churnColor("low risk")).toBe("#22c55e");
  });

  it("returns gray for unknown", () => {
    expect(churnColor("")).toBe("#6b7280");
  });
});

describe("tierColor", () => {
  it("returns amber for gold", () => {
    expect(tierColor("gold")).toBe("#f59e0b");
  });

  it("returns gray for unknown tier", () => {
    expect(tierColor("unknown")).toBe("#6b7280");
  });
});

describe("wheelTargetRotation", () => {
  it("lands the first segment (index 0) under the top pointer", () => {
    // 4 segments, segAngle=90, center of seg 0 at 45deg → rotate 315 to align,
    // plus 5 full spins = 1800 → total 2115.
    const rot = wheelTargetRotation(0, 4, 5, 0);
    expect(rot).toBe(315 + 1800);
    // The final resting position (mod 360) must align segment center to top.
    expect(rot % 360).toBe(315);
  });

  it("brings the winning segment center to the top (12 o'clock)", () => {
    const segmentCount = 6;
    const segAngle = 360 / segmentCount;
    for (let idx = 0; idx < segmentCount; idx++) {
      const rot = wheelTargetRotation(idx, segmentCount, 5, 0);
      // After rotating the wheel by `rot`, the segment center originally at
      // (idx+0.5)*segAngle moves to (center + rot) mod 360, which should be 0 (top).
      const finalPos = ((idx + 0.5) * segAngle + rot) % 360;
      expect(Math.round(finalPos)).toBe(0);
    }
  });

  it("always spins forward from the current rotation", () => {
    const current = 2115;
    const rot = wheelTargetRotation(2, 8, 5, current);
    expect(rot).toBeGreaterThan(current);
    expect(rot).toBeGreaterThanOrEqual(current + 5 * 360);
  });

  it("returns currentRotation for an empty wheel", () => {
    expect(wheelTargetRotation(0, 0, 5, 120)).toBe(120);
  });
});

describe("relativeTime", () => {
  const now = new Date("2026-05-27T12:00:00Z");

  it("returns 'just now' for very recent times", () => {
    expect(relativeTime("2026-05-27T11:59:40Z", now)).toBe("just now");
  });

  it("returns minutes ago", () => {
    expect(relativeTime("2026-05-27T11:30:00Z", now)).toBe("30m ago");
  });

  it("returns hours ago", () => {
    expect(relativeTime("2026-05-27T09:00:00Z", now)).toBe("3h ago");
  });

  it("returns days ago", () => {
    expect(relativeTime("2026-05-25T12:00:00Z", now)).toBe("2d ago");
  });

  it("handles null", () => {
    expect(relativeTime(null, now)).toBe("—");
  });
});
