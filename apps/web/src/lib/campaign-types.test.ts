import { describe, it, expect } from "vitest";
import { CAMPAIGN_TYPES } from "@fbgroup/api-client";

describe("CAMPAIGN_TYPES", () => {
  it("lists the 6 supported campaign types", () => {
    expect(CAMPAIGN_TYPES).toEqual([
      "whatsapp_promo",
      "birthday",
      "winback",
      "weekday_boost",
      "new_customer_return",
      "vip_reward",
    ]);
  });

  it("has no duplicate types", () => {
    expect(new Set(CAMPAIGN_TYPES).size).toBe(CAMPAIGN_TYPES.length);
  });
});
