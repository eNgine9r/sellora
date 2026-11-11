import type { BankPaymentKind, BankPaymentRail } from "@/types/bank-payment-evidence";

export type BankImportRow = {
  provider_account_id: string;
  external_reference: string;
  rail: BankPaymentRail;
  kind: BankPaymentKind;
  amount_minor: number;
  currency: "UAH";
  occurred_at: string;
  is_hold: boolean;
  invoice_id: string | null;
  order_number: string | null;
};

const rails = new Set(["BANK_IBAN", "FOP_CARD", "MONO_ACQUIRING_LINK", "UNKNOWN_ACCOUNT_TRANSFER"]);
const kinds = new Set(["CUSTOMER_PAYMENT", "UNCLASSIFIED_CREDIT", "ACQUIRING_PAYOUT", "REFUND"]);
const required = ["provider_account_id", "external_reference", "rail", "kind", "amount_uah", "occurred_at"];

function splitCsv(raw: string): string[][] {
  const first = raw.slice(0, raw.indexOf("\n") < 0 ? raw.length : raw.indexOf("\n"));
  const delimiter = first.includes(";") ? ";" : first.includes("\t") ? "\t" : ",";
  const result: string[][] = [], fields: string[] = [];
  let field = "", quote = false;
  for (let i = 0; i < raw.length; i++) {
    const ch = raw[i];
    if (ch === '"') {
      if (quote && raw[i + 1] === '"') { field += '"'; i++; }
      else if (quote || field.length === 0) quote = !quote;
      else throw new Error("Malformed CSV quote");
    } else if (!quote && ch === delimiter) {
      fields.push(field); field = "";
    } else if (!quote && (ch === "\n" || ch === "\r")) {
      if (ch === "\r" && raw[i + 1] === "\n") i++;
      fields.push(field); field = "";
      if (fields.some(s => s.trim())) result.push([...fields]);
      fields.length = 0;
    } else { field += ch; }
  }
  if (quote) throw new Error("Unclosed CSV quote");
  fields.push(field);
  if (fields.some(s => s.trim())) result.push(fields);
  return result;
}

function minorFromUah(value: string): number {
  const amount = value.trim();
  if (!/^(?:0|[1-9]\d{0,11})(?:[.,]\d{1,2})?$/.test(amount)) throw new Error("Invalid UAH amount");
  const [whole, fraction = ""] = amount.replace(",", ".").split(".");
  const minor = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(minor) || minor <= 0 || minor >= 100_000_000_000_000) throw new Error("Amount out of range");
  return minor;
}

function reference(value: string | undefined, min: number, max: number): string | null {
  if (!value?.trim()) return null;
  const trimmed = value.trim();
  if (trimmed.length < min || trimmed.length > max || /[\r\n\0]/.test(trimmed)) throw new Error("Invalid reference");
  return trimmed;
}

export function parseBankEvidenceCsv(raw: string): BankImportRow[] {
  if (raw.length > 1_000_000) throw new Error("File too large (max 1 MB)");
  const lines = splitCsv(raw.replace(/^\uFEFF/, ""));
  if (lines.length < 2 || lines.length > 201) throw new Error("Use a header and 1–200 payment rows");
  const header = lines[0].map(v => v.trim().toLowerCase());
  if (new Set(header).size !== header.length) throw new Error("Duplicate CSV columns");
  for (const key of required) if (!header.includes(key)) throw new Error("Required column: " + key);
  const at = (line: string[], key: string) => line[header.indexOf(key)] ?? "";
  return lines.slice(1).map((line, index) => {
    if (line.length !== header.length) throw new Error("Wrong CSV column count at line " + (index + 2));
    const account = reference(at(line, "provider_account_id"), 3, 128);
    const event = reference(at(line, "external_reference"), 3, 160);
    if (!account || !event) throw new Error("Account and unique transaction id are required at line " + (index + 2));
    const rail = at(line, "rail").trim(), kind = at(line, "kind").trim();
    if (!rails.has(rail) || !kinds.has(kind)) throw new Error("Invalid payment method or kind at line " + (index + 2));
    const dateText = at(line, "occurred_at").trim();
    if (!/(?:Z|[+-]\d{2}:\d{2})$/.test(dateText)) throw new Error("Timestamp with explicit timezone required at line " + (index + 2));
    const date = new Date(dateText);
    if (!Number.isFinite(date.getTime())) throw new Error("Invalid date at line " + (index + 2));
    const hold = at(line, "is_hold").trim().toLowerCase();
    if (hold && hold !== "true" && hold !== "false") throw new Error("is_hold must be true/false");
    return {
      provider_account_id: account,
      external_reference: event,
      rail: rail as BankPaymentRail,
      kind: kind as BankPaymentKind,
      amount_minor: minorFromUah(at(line, "amount_uah")),
      currency: "UAH",
      occurred_at: date.toISOString(),
      is_hold: hold === "true",
      invoice_id: reference(at(line, "invoice_id"), 3, 160),
      order_number: reference(at(line, "order_number"), 1, 30),
    };
  });
}
