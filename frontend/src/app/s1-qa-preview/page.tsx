export default function OrderQaPreview() {
  return (
    <main style={{ margin: "0 auto", maxWidth: 420, padding: 12 }}>
      <h1>Order form — mobile viewport QA</h1>
      <p>Preview only. Do not submit real orders or issue waybills.</p>
      <iframe title="Sellora mobile order QA" src="/s1-qa-preview/fixture" width="390" height="800" style={{ maxWidth: "100%", border: "1px solid #888" }} />
    </main>
  );
}
