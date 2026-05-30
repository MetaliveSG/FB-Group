"use client";

// Country-code picker for the phone field. Region codes mirror the backend's
// SUPPORTED_REGIONS (app/core/phone.py). The user types the local number; the
// backend normalizes to E.164 using the chosen region (handles trunk prefixes,
// e.g. MY '016…' → '+6016…'). Default region is SG (later: from the outlet region).
export const COUNTRIES = [
  { region: "SG", dial: "+65", flag: "🇸🇬", label: "Singapore" },
  { region: "MY", dial: "+60", flag: "🇲🇾", label: "Malaysia" },
  { region: "ID", dial: "+62", flag: "🇮🇩", label: "Indonesia" },
  { region: "TH", dial: "+66", flag: "🇹🇭", label: "Thailand" },
] as const;

export const DEFAULT_REGION = "SG";

export function dialFor(region: string): string {
  return COUNTRIES.find((c) => c.region === region)?.dial ?? "+65";
}

export default function CountrySelect({
  region,
  onChange,
  disabled,
}: {
  region: string;
  onChange: (region: string) => void;
  disabled?: boolean;
}) {
  return (
    <select
      className="country-select"
      value={region}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Country code"
    >
      {COUNTRIES.map((c) => (
        <option key={c.region} value={c.region}>
          {c.flag} {c.dial}
        </option>
      ))}
    </select>
  );
}
