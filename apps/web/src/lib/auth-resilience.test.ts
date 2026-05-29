import { describe, it, expect } from "vitest";
import { shouldAttemptRefresh, AUTH_ERROR_CODES } from "@fbgroup/api-client";

describe("shouldAttemptRefresh", () => {
  it("returns true for a 401 with no error code", () => {
    expect(shouldAttemptRefresh(401)).toBe(true);
    expect(shouldAttemptRefresh(401, undefined)).toBe(true);
    expect(shouldAttemptRefresh(401, "UNKNOWN")).toBe(true);
  });

  it("returns true for 401 with a known auth error code", () => {
    for (const code of AUTH_ERROR_CODES) {
      expect(shouldAttemptRefresh(401, code)).toBe(true);
    }
  });

  it("returns true for 401 + not_found (stale subject id after reseed)", () => {
    expect(shouldAttemptRefresh(401, "not_found")).toBe(true);
  });

  it("returns true for ANY 401 regardless of code", () => {
    // Code is no longer whitelisted — any 401 is treated as an auth failure.
    expect(shouldAttemptRefresh(401, "rate_limited")).toBe(true);
    expect(shouldAttemptRefresh(401, "some_other_code")).toBe(true);
  });

  it("returns false for non-401 statuses", () => {
    expect(shouldAttemptRefresh(403, "token_expired")).toBe(false);
    expect(shouldAttemptRefresh(500)).toBe(false);
    expect(shouldAttemptRefresh(200)).toBe(false);
    expect(shouldAttemptRefresh(404, "not_found")).toBe(false);
  });
});
