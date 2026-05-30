import type { MenuItem } from "@fbgroup/api-client";

/** Live menu search — case-insensitive match on item name OR description.
 *  Empty/whitespace query returns [] (the page shows category sections instead). */
export function filterMenuItems(items: MenuItem[], query: string): MenuItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return items.filter(
    (i) => i.name.toLowerCase().includes(q) || (i.description ?? "").toLowerCase().includes(q)
  );
}
