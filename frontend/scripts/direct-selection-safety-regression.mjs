import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync("frontend/src/app/direct/page.tsx","utf8");
assert.match(page, /const selectionTargetRef = useRef<string \| null>\(null\)/);
assert.match(page, /selectionTargetRef\.current = conversationId/);
assert.match(page, /selectionTargetRef\.current = null/);
assert.match(page, /if \(selectionTargetRef\.current && selectionTargetRef\.current !== conversationId\) return null/);
assert.match(page, /const safeSelectedConversationId = \(\) =>/);
assert.match(page, /onEnsureLead=\{\(\) => \{\s*const conversationId = safeSelectedConversationId\(\)/);
assert.match(page, /onEnsureCustomer=\{\(\) => \{\s*const conversationId = safeSelectedConversationId\(\)/);
assert.match(page, /onConfirmOrderEvidence=\{\(\) => \{\s*if \(!safeSelectedConversationId\(\)\) return/);
console.log("Direct selection-switch mutation safety checks passed.");
