# FB Group F&B Platform — Web Frontend

Next.js 14 App Router + TypeScript frontend for the Singapore F&B CRM & QR Ordering PoC.

## Prerequisites

- Node.js 18+ (LTS recommended)
- The FastAPI backend running at `http://localhost:8000` (see `apps/api/`)

## Quick Start

```bash
cd apps/web
npm install
npm run dev
```

App opens at **http://localhost:3000**.

## Environment

Create `.env.local` (already included) or set:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server (hot reload) |
| `npm run build` | Production build |
| `npm start` | Serve production build |
| `npm test` | Run Vitest unit tests |

## Demo Walkthrough

### Customer QR Ordering
1. Open **http://localhost:3000**
2. The sample QR token `0b70cea7-01` is pre-filled — click **Open Table Ordering**
3. Browse menu, add items (with modifier selection)
4. Click **Login to Order** → enter any phone number → OTP auto-fills in dev mode
5. Click **Place Order** → choose payment method → **Pay**
6. See points earned on the success screen

### Merchant Dashboard
1. Click **Go to Merchant Login** on the home page (or visit `/merchant/login`)
2. Credentials are pre-filled: `owner@makan.sg` / `Password123!`
3. Dashboard shows segment chips, KPI cards, revenue line chart, top-items bar chart
4. Click any customer row to see their full profile
5. Add tags / notes from the profile page

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home / demo launcher |
| `/t/[token]` | QR table ordering (customer flow) |
| `/merchant/login` | Staff login |
| `/merchant/crm` | CRM dashboard (staff only) |
| `/merchant/crm/[id]` | Customer profile (staff only) |

## Architecture

```
apps/web/
  src/
    app/                   # Next.js App Router pages
      layout.tsx
      globals.css
      page.tsx             # Home
      t/[token]/page.tsx   # Customer QR ordering
      merchant/
        login/page.tsx
        crm/page.tsx
        crm/[id]/page.tsx
    components/
      BarChart.tsx          # Inline SVG bar chart
      LineChart.tsx         # Inline SVG line chart
    lib/
      auth.ts              # localStorage token helpers
      api.ts               # API client instantiation
      format.ts            # Formatting utilities + cart math
      format.test.ts       # Vitest unit tests

packages/api-client/
  src/index.ts             # Typed API client & TS interfaces
```

## Notes

- No Tailwind — styling via `globals.css` with CSS custom properties
- Charts are pure SVG (no library)
- JWT stored in `localStorage` (customer + staff keys separate)
- API client at `@fbgroup/api-client` resolved via `tsconfig.json` path alias
