import { describe, it, expect } from "vitest";
import { filterMenuItems } from "./menu";
import type { MenuItem } from "@fbgroup/api-client";

const item = (over: Partial<MenuItem>): MenuItem => ({
  id: over.id ?? "x",
  name: over.name ?? "Item",
  description: over.description ?? "",
  price: over.price ?? 5,
  image_url: over.image_url ?? null,
  is_available: over.is_available ?? true,
  modifiers: over.modifiers ?? [],
});

const items: MenuItem[] = [
  item({ id: "1", name: "Fish Ball Noodle" }),
  item({ id: "2", name: "Curry Rice", description: "Hainanese curry" }),
  item({ id: "3", name: "Teh Tarik" }),
];

describe("filterMenuItems", () => {
  it("returns [] for an empty or whitespace query", () => {
    expect(filterMenuItems(items, "")).toEqual([]);
    expect(filterMenuItems(items, "   ")).toEqual([]);
  });

  it("matches on name, case-insensitively", () => {
    expect(filterMenuItems(items, "fish").map((i) => i.id)).toEqual(["1"]);
    expect(filterMenuItems(items, "TARIK").map((i) => i.id)).toEqual(["3"]);
  });

  it("matches on description too", () => {
    expect(filterMenuItems(items, "hainanese").map((i) => i.id)).toEqual(["2"]);
  });

  it("returns empty array when nothing matches", () => {
    expect(filterMenuItems(items, "pizza")).toEqual([]);
  });
});
