"use client";

import { Icons } from "./ui";

// Sticky menu chrome: a search field + a horizontally-scrollable category bar with
// scroll-spy (the active category is driven by the page's IntersectionObserver).
// Presentational only — the page owns scroll-spy state and the scroll-to-category.
export default function MenuCategoryNav({
  categories,
  activeCat,
  onSelect,
  search,
  onSearch,
  showSearch,
}: {
  categories: { id: string; name: string }[];
  activeCat: string | null;
  onSelect: (id: string) => void;
  search: string;
  onSearch: (q: string) => void;
  showSearch: boolean;
}) {
  const showCats = categories.length > 1 && !search;
  if (!showSearch && !showCats) return null;

  return (
    <div className="menu-nav">
      {showSearch && (
        <div className="menu-search">
          <Icons.Search size={18} aria-hidden />
          <input
            type="text"
            inputMode="search"
            placeholder="Search the menu…"
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            aria-label="Search the menu"
          />
          {search && (
            <button type="button" className="menu-search__clear" aria-label="Clear search" onClick={() => onSearch("")}>
              <Icons.X size={16} />
            </button>
          )}
        </div>
      )}
      {showCats && (
        <div className="menu-cats" role="tablist" aria-label="Menu categories">
          {categories.map((c) => (
            <button
              key={c.id}
              type="button"
              role="tab"
              aria-selected={activeCat === c.id}
              className={`menu-cat${activeCat === c.id ? " menu-cat--active" : ""}`}
              onClick={() => onSelect(c.id)}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
