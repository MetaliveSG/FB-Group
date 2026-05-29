"use client";

import { useState } from "react";
import {
  Button,
  Card,
  ListItem,
  Stepper,
  Badge,
  Skeleton,
  EmptyState,
  Sheet,
  CoinBalance,
  TierProgress,
  BottomNav,
  Icons,
} from "@/components/ui";

/* A living gallery of the FB Group UI kit in the warm theme.
   Visit /showcase to review every component + token before applying to screens. */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: "var(--space-6)" }}>
      <h2
        style={{
          fontSize: "var(--text-sm)",
          fontWeight: "var(--weight-bold)" as unknown as number,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--color-text-muted)",
          margin: "0 0 var(--space-3)",
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}>{children}</div>;
}

const BRAND = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900];
const NEUTRAL = [0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900];

export default function Showcase() {
  const [qty, setQty] = useState(1);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [tab, setTab] = useState("menu");

  return (
    <div style={{ maxWidth: 440, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--color-bg)" }}>
      {/* Header */}
      <header
        style={{
          padding: "var(--space-5) var(--space-4) var(--space-4)",
          background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))",
          color: "#fff",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: "var(--text-2xl)", fontWeight: 900, lineHeight: 1.1 }}>UI Kit</div>
            <div style={{ opacity: 0.85, fontSize: "var(--text-sm)", marginTop: 2 }}>Warm theme · component gallery</div>
          </div>
          <CoinBalance coins={1280} />
        </div>
      </header>

      <main style={{ flex: 1, padding: "var(--space-5) var(--space-4)" }}>
        {/* Colors */}
        <Section title="Brand — flame">
          <Row>
            {BRAND.map((s) => (
              <div key={s} style={{ textAlign: "center" }}>
                <div style={{ width: 30, height: 30, borderRadius: "var(--radius-sm)", background: `var(--brand-${s})`, border: "1px solid var(--color-border)" }} />
                <div style={{ fontSize: 9, color: "var(--color-text-muted)", marginTop: 2 }}>{s}</div>
              </div>
            ))}
          </Row>
        </Section>

        <Section title="Neutrals — stone (warm)">
          <Row>
            {NEUTRAL.map((s) => (
              <div key={s} style={{ textAlign: "center" }}>
                <div style={{ width: 26, height: 26, borderRadius: "var(--radius-sm)", background: `var(--neutral-${s})`, border: "1px solid var(--color-border)" }} />
                <div style={{ fontSize: 9, color: "var(--color-text-muted)", marginTop: 2 }}>{s}</div>
              </div>
            ))}
          </Row>
        </Section>

        <Section title="Accent / Gold / Semantic">
          <Row>
            {[
              ["accent", "var(--color-accent)"],
              ["gold", "var(--color-gold)"],
              ["success", "var(--color-success)"],
              ["danger", "var(--color-danger)"],
              ["warning", "var(--color-warning)"],
            ].map(([name, val]) => (
              <div key={name} style={{ textAlign: "center" }}>
                <div style={{ width: 44, height: 30, borderRadius: "var(--radius-sm)", background: val }} />
                <div style={{ fontSize: 9, color: "var(--color-text-muted)", marginTop: 2 }}>{name}</div>
              </div>
            ))}
          </Row>
        </Section>

        {/* Type scale */}
        <Section title="Type scale">
          <Card pad>
            {([["5xl", 48], ["3xl", 30], ["xl", 20], ["base", 16], ["sm", 14], ["xs", 12]] as const).map(([name, px]) => (
              <div key={name} style={{ display: "flex", alignItems: "baseline", gap: "var(--space-3)", marginBottom: 6 }}>
                <span style={{ width: 36, fontSize: 11, color: "var(--color-text-muted)" }}>{name}</span>
                <span style={{ fontSize: px, fontWeight: 700, color: "var(--color-text)" }}>Makan {px}</span>
              </div>
            ))}
          </Card>
        </Section>

        {/* Buttons */}
        <Section title="Buttons">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <Row>
              <Button variant="primary" leftIcon={Icons.ShoppingCart}>Add to Cart</Button>
              <Button variant="accent">Redeem</Button>
              <Button variant="secondary">Secondary</Button>
            </Row>
            <Row>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Cancel</Button>
              <Button variant="primary" disabled>Disabled</Button>
              <Button variant="primary" loading>Loading</Button>
            </Row>
            <Row>
              <Button size="sm" variant="primary">Small</Button>
              <Button size="lg" variant="primary" leftIcon={Icons.Trophy}>Large</Button>
            </Row>
            <Button block variant="primary" size="lg" leftIcon={Icons.CreditCard}>Checkout · S$24.00</Button>
          </div>
        </Section>

        {/* Badges */}
        <Section title="Badges / Chips">
          <Row>
            <Badge>Default</Badge>
            <Badge tone="success">Champion</Badge>
            <Badge tone="warning">At risk</Badge>
            <Badge tone="danger">Churned</Badge>
            <Badge tone="gold">VIP</Badge>
          </Row>
        </Section>

        {/* Stepper + Coin + Tier */}
        <Section title="Stepper · Coins · Tier progress">
          <Card pad>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-4)" }}>
              <span style={{ fontWeight: 600 }}>Quantity</span>
              <Stepper value={qty} onChange={setQty} />
            </div>
            <div style={{ marginBottom: "var(--space-4)" }}>
              <CoinBalance coins={1280} />
            </div>
            <TierProgress pct={64} fromLabel="320 coins to Gold" toLabel="64%" />
          </Card>
        </Section>

        {/* Cards + List */}
        <Section title="Card · ListItem">
          <Card flush>
            <ListItem icon={Icons.Utensils} title="Fish Ball Noodle" meta="S$5.50 · Hawker Mains" chevron onClick={() => {}} />
            <ListItem icon={Icons.Gift} title="Free Teh Tarik" meta="150 coins" right={<Badge tone="gold">Reward</Badge>} />
            <ListItem icon={Icons.Receipt} title="Order #1042" meta="2 items · 12 May" chevron onClick={() => {}} />
          </Card>
        </Section>

        {/* Skeletons */}
        <Section title="Skeleton (loading)">
          <Card pad>
            <Skeleton width="60%" height={18} style={{ marginBottom: 10 }} />
            <Skeleton width="100%" height={12} style={{ marginBottom: 6 }} />
            <Skeleton width="85%" height={12} />
          </Card>
        </Section>

        {/* Empty + Sheet */}
        <Section title="EmptyState · Sheet">
          <Card flush style={{ marginBottom: "var(--space-3)" }}>
            <EmptyState icon={Icons.ShoppingCart} title="Your cart is empty">
              Add items from the menu to get started.
            </EmptyState>
          </Card>
          <Button block variant="secondary" onClick={() => setSheetOpen(true)}>
            Open bottom sheet
          </Button>
        </Section>
      </main>

      {/* Bottom tab bar */}
      <BottomNav
        active={tab}
        items={[
          { key: "menu", label: "Menu", icon: Icons.Utensils, onClick: () => setTab("menu") },
          { key: "rewards", label: "Rewards", icon: Icons.Gift, onClick: () => setTab("rewards") },
          { key: "orders", label: "Orders", icon: Icons.Receipt, onClick: () => setTab("orders") },
          { key: "me", label: "Me", icon: Icons.User, onClick: () => setTab("me") },
        ]}
      />

      <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)}>
        <div style={{ fontSize: "var(--text-xl)", fontWeight: 800, marginBottom: "var(--space-2)" }}>Confirm order</div>
        <p style={{ color: "var(--color-text-muted)", marginTop: 0 }}>
          This is a bottom sheet — the pattern we&apos;ll use for checkout, item options, and confirmations.
        </p>
        <Button block variant="primary" size="lg" leftIcon={Icons.Check} onClick={() => setSheetOpen(false)}>
          Confirm
        </Button>
      </Sheet>
    </div>
  );
}
