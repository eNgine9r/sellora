import type { CodImportRow, CodImportSource } from "@/types/cod-reconciliation";

function normalizeHeader(value: string) {
  return value.normalize("NFKC").replace(/^\uFEFF/, "").toLowerCase()
    .replace(/[\s_\-–—.:№()]+/g, "");
}

function parseCsv(text: string): string[][] {
  const first = text.split(/\r?\n/)[0] ?? "";
  const counts = [",", ";", "\t"].map((char) => [char, first.split(char).length - 1] as const);
  const delimiter = counts.sort((a, b) => b[1] - a[1])[0][0];
  const result: string[][] = [];
  let fields: string[] = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && ch === delimiter) {
      fields.push(field); field = "";
    } else if (!quoted && (ch === "\r" || ch === "\n")) {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      fields.push(field); field = "";
      if (fields.some((v) => v.trim())) result.push(fields);
      fields = [];
    } else {
      field += ch;
    }
  }
  if (quoted) throw new Error("CSV contains an unclosed quote.");
  fields.push(field);
  if (fields.some((v) => v.trim())) result.push(fields);
  return result;
}

const alias: Record<string, string[]> = {
  ttn: ["trackingnumber", "ttn", "ттн", "номереттн", "номерекспреснакладної", "номернакладної", "номервідправлення", "номерен", "номерпосилки"],
  amount: ["grossamount", "amount", "сумаприйнятихкоштів", "сумаприйнятих", "суманадходження", "сумаклієнта", "сумаоплати", "сумаплатежу", "сума"],
  fee: ["feeamount", "fee", "комісія", "комісіязапереказ", "комісіяnovapay"],
  paid: ["paidat", "paymentdate", "датаплатежу", "датаоплати", "датапереказу", "дата"],
  reference: ["reference", "externalreference", "idтранзакції", "номероперації", "номертранзакції", "номерплатежу", "номерпереказу", "ідентифікаторплатежу"],
};

function money(value: string, emptyAllowed = false) {
  const cleaned = value.replace(/[\s\u00a0\u202f₴грн]/gi, "").replace(",", ".").trim();
  if (!cleaned && emptyAllowed) return "0.00";
  if (!/^(?:0|[1-9]\d*)(?:\.\d{1,2})?$/.test(cleaned)) throw new Error("Invalid monetary value: " + value);
  return Number(cleaned).toFixed(2);
}

function normalizedDate(raw: string) {
  const trimmed = raw.trim();
  let match = trimmed.match(/^(\d{2})\.(\d{2})\.(\d{4})/);
  let iso: string;
  if (match) iso = match[3] + "-" + match[2] + "-" + match[1];
  else {
    match = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) throw new Error("Invalid payment date: " + raw);
    iso = match[1] + "-" + match[2] + "-" + match[3];
  }
  const check = new Date(iso + "T12:00:00Z");
  if (Number.isNaN(check.getTime()) || check.toISOString().slice(0, 10) !== iso)
    throw new Error("Invalid payment date: " + raw);
  // When only a calendar date is supplied, use UTC noon; never fabricate a
  // precise bank transaction time.
  return iso + "T12:00:00Z";
}

export function parseCodRegisterCsv(text: string, source: CodImportSource): CodImportRow[] {
  if (text.length > 1_500_000) throw new Error("File exceeds 1.5 MB");
  const grid = parseCsv(text);
  if (grid.length < 2) throw new Error("File needs a header and at least one payment row");
  if (grid.length > 301) throw new Error("Maximum 300 rows per import");
  const headers = grid[0].map(normalizeHeader);
  const idx = (key: keyof typeof alias) => headers.findIndex((v) => alias[key].includes(v));
  const amountCol = idx("amount"), dateCol = idx("paid");
  if (amountCol < 0 || dateCol < 0) throw new Error("Required columns: amount and payment date");
  const ttnCol = idx("ttn"), feeCol = idx("fee"), refCol = idx("reference");
  return grid.slice(1).map((line, i) => {
    const gross_amount = money(line[amountCol] ?? "");
    const fee_amount = money(feeCol >= 0 ? line[feeCol] ?? "" : "", true);
    const paid_at = normalizedDate(line[dateCol] ?? "");
    const tracking_number = ttnCol >= 0 ? (line[ttnCol] ?? "").replace(/\s/g, "") || null : null;
    const providedRef = refCol >= 0 ? (line[refCol] ?? "").trim() : "";
    if (!tracking_number && !providedRef) {
      throw new Error("Rows without a TTN need a unique transaction reference (line " + (i + 2) + ")");
    }
    // Deterministic fallback supports safe repeat imports of the same records.
    const reference = (providedRef || [source, tracking_number || "NO_TTN", paid_at.slice(0, 10), gross_amount, fee_amount].join(":")).slice(0, 160);
    if (reference.length < 3) throw new Error("Invalid reference at line " + (i + 2));
    return { source, reference, tracking_number, gross_amount, fee_amount, paid_at };
  });
}
