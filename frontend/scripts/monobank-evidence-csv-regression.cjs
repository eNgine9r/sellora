"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");

const source = fs.readFileSync("src/lib/bank-payment-evidence-csv.ts", "utf8");
const { outputText, diagnostics } = ts.transpileModule(source, {
  fileName: "bank-payment-evidence-csv.ts",
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  reportDiagnostics: true,
});
assert.equal(diagnostics?.filter(d => d.category === ts.DiagnosticCategory.Error).length, 0);
const exports = {};
vm.runInNewContext(outputText, { exports, require }, { timeout: 1500 });
const parse = exports.parseBankEvidenceCsv;
const H = "provider_account_id,external_reference,rail,kind,amount_uah,occurred_at,is_hold,invoice_id,order_number";
const row = "mono-acc-01,tx-001,BANK_IBAN,CUSTOMER_PAYMENT,749.50,2026-11-11T08:00:00Z,false,,SL-1042";

const parsed = parse(H + "\n" + row);
assert.equal(parsed.length, 1);
assert.equal(parsed[0].amount_minor, 74950);
assert.equal(parsed[0].currency, "UAH");
assert.equal(parsed[0].order_number, "SL-1042");
assert.equal(parsed[0].kind, "CUSTOMER_PAYMENT");

const semi = H.replaceAll(",", ";") + "\n" + row.replace("749.50", "749,50").replaceAll(",", ";").replace("749;50", "749,50");
assert.equal(parse(semi)[0].amount_minor, 74950);

function rejects(csv) { assert.throws(() => parse(csv)); }
rejects(H + "\n" + row.replace("749.50", "=1+1"));
rejects(H + "\n" + row.replace("749.50", "-1"));
rejects(H + "\n" + row.replace("749.50", "749.999"));
rejects(H + "\n" + row.replace("2026-11-11T08:00:00Z", "2026-11-11T08:00:00"));
rejects(H + "\n" + row.replace("tx-001", ""));
rejects(H + "\n" + row.replace("BANK_IBAN", "UNKNOWN_RAIL"));
rejects(H + "\n" + row.replace("false", "yes"));
rejects(H + ",amount_uah\n" + row + ",749");
rejects(H + "\n" + Array.from({ length: 201 }, (_, i) => row.replace("tx-001", "tx-" + i)).join("\n"));
rejects(H + "\n" + row.replace("749.50", "0"));
rejects(H + "\n" + row.replace("749.50", "999999999999999999"));
rejects(H + "\n" + row + ",extra");
console.log("MONOBANK_CSV_REGRESSION_PASS");
