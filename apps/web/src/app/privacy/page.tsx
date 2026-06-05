// Privacy notice shown at the PDPA consent checkbox (customer signup). Plain, demo-appropriate text.

export const metadata = { title: "Privacy Policy — FB Group" };

export default function PrivacyPage() {
  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "32px 20px", lineHeight: 1.65, color: "#1f2937" }}>
      <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>Privacy Policy</h1>
      <p style={{ color: "#6b7280", marginTop: 0 }}>How we collect, use, and protect your personal data (Singapore PDPA).</p>

      <h2 style={h2}>What we collect</h2>
      <p>Your mobile number, name (if provided), order history, and loyalty activity at the merchant whose QR you scanned.</p>

      <h2 style={h2}>Why we use it (purposes)</h2>
      <ul>
        <li>To take and fulfil your order and process payment.</li>
        <li>To run the merchant&apos;s loyalty programme — points, tiers, rewards, and games.</li>
        <li>If you opt in: to send you offers, rewards, and updates (you can withdraw this anytime).</li>
      </ul>

      <h2 style={h2}>Consent &amp; your choices</h2>
      <p>
        We collect and use your data only with your consent. Marketing messages are sent only if you give
        express opt-in. You may <strong>withdraw consent</strong> (including marketing) at any time from your
        account, after which we stop the relevant use of your data.
      </p>

      <h2 style={h2}>Sharing &amp; retention</h2>
      <p>
        Your data is shared only with the merchant you transacted with and our service providers (e.g. payment,
        messaging), and is kept only as long as needed for these purposes or as the law requires.
      </p>

      <h2 style={h2}>Contact</h2>
      <p>For access, correction, or withdrawal requests, contact the merchant or our Data Protection Officer.</p>

      <p style={{ marginTop: 28 }}><a href="/">← Back</a></p>
    </main>
  );
}

const h2: React.CSSProperties = { fontSize: 18, fontWeight: 700, marginTop: 24, marginBottom: 6 };
