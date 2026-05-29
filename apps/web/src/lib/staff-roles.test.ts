import { describe, it, expect } from "vitest";
import { STAFF_ROLES } from "@fbgroup/api-client";

describe("STAFF_ROLES", () => {
  it("lists the 4 assignable roles", () => {
    expect(STAFF_ROLES).toEqual([
      "merchant_owner",
      "brand_manager",
      "outlet_manager",
      "staff",
    ]);
  });

  it("has no duplicate roles", () => {
    expect(new Set(STAFF_ROLES).size).toBe(STAFF_ROLES.length);
  });
});
