import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const frontendRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const read = (relative) => fs.readFileSync(path.join(frontendRoot, relative), "utf8");
const failures = [];
const notes = [];

function requireText(relative, expected, label) {
  const source = read(relative);
  if (!source.includes(expected)) failures.push(`${label}: missing ${JSON.stringify(expected)} in ${relative}`);
}

requireText("src/components/app-shell.tsx", "floating-capsule five-primary-links profile-sheet subtle-active-state", "mobile navigation contract");
requireText("src/components/app-shell.tsx", "bottom-[max(0.75rem,env(safe-area-inset-bottom))]", "bottom navigation safe area");
requireText("src/components/ui/primitives.tsx", "min-h-11", "minimum touch target");
requireText("src/components/ui/overlay.tsx", "max-h-[96dvh]", "overlay viewport boundary");
requireText("src/components/ui/overlay.tsx", "overflow-x-hidden overflow-y-auto overscroll-contain", "overlay internal scrolling");
requireText("src/components/ui/bottom-sheet.tsx", "max-h-[94dvh]", "bottom sheet viewport boundary");
requireText("src/components/mobile-more-sheet.tsx", "border-border-subtle bg-surface-2", "mobile action tokenization");
requireText("src/components/form-dialog.tsx", "<Modal open", "form dialog shared overlay");
requireText("src/components/confirm-action-dialog.tsx", "<ConfirmationDialog open", "confirmation shared overlay");
requireText("src/components/edit-record-dialog.tsx", "actions.saveChanges", "localized edit action");
requireText("src/components/filter-controls.tsx", "FilterBar as SharedFilterBar", "shared filter primitives");
requireText("src/features/leads/components/lead-form.tsx", "Button, FormField, Input, Select, Textarea", "lead form shared controls");
requireText("src/features/customers/components/customer-form.tsx", "Button, FormField, Input", "customer form shared controls");
requireText("src/features/products/components/product-form.tsx", "Button, FormField, Input, Select, Textarea", "product form shared controls");
requireText("src/features/products/components/product-variant-form.tsx", "Button, FormField, Input, Select", "variant form shared controls");
requireText("src/features/advertising/components/campaign-form.tsx", "Button, FormField, Input, Select, Textarea", "campaign form shared controls");
requireText("src/features/integrations/components/instagram-messaging-integration-card.tsx", "w-full min-w-0 max-w-full overflow-hidden", "Instagram card mobile width contract");
requireText("scripts/mobile-ui-audit.mjs", "discoverAppRoutes", "exhaustive App Router discovery");
requireText("scripts/mobile-ui-audit.mjs", "dynamicTemplates", "dynamic route inventory");
requireText("src/app/direct/page.tsx", "w-[92vw] max-w-md flex-col overflow-hidden", "Direct AI drawer bounded width");
requireText("src/app/direct/page.tsx", "sellora-scrollbar min-h-0 flex-1 overflow-y-auto", "Direct AI drawer internal scroll");
requireText("src/app/direct/page.tsx", "aria-label={t(\"actions.close\")}", "Direct AI drawer localized close action");

const forbidden = [
  ["src/components/mobile-more-sheet.tsx", "bg-violet-600", "page-local violet primary button"],
  ["src/components/mobile-more-sheet.tsx", "bg-red-50", "page-local destructive button"],
  ["src/components/ui/overlay.tsx", "aria-label=\"Close\"", "non-localized close label"],
  ["src/components/ui/primitives.tsx", "min-h-8", "undersized shared button"],
  ["src/components/form-dialog.tsx", "fixed inset-0", "duplicated form overlay"],
  ["src/components/confirm-action-dialog.tsx", "Working…", "English confirmation progress action"],
  ["src/components/edit-record-dialog.tsx", "Saving…", "English edit progress action"],
  ["src/components/edit-record-dialog.tsx", "Save changes", "English edit submit action"],
  ["src/components/filter-controls.tsx", "bg-blue", "page-local blue filter action"],
  ["src/features/leads/components/lead-form.tsx", "bg-blue", "page-local lead submit action"],
  ["src/features/customers/components/customer-form.tsx", "bg-blue", "page-local customer submit action"],
  ["src/features/products/components/product-form.tsx", "bg-blue", "page-local product submit action"],
  ["src/features/products/components/product-variant-form.tsx", "bg-blue", "page-local variant submit action"],
  ["src/features/advertising/components/campaign-form.tsx", "bg-blue", "page-local campaign submit action"],
  ["src/features/leads/components/lead-form.tsx", "Create lead", "English lead submit copy"],
  ["src/features/products/components/product-variant-form.tsx", "Create variant", "English variant submit copy"],
];
for (const [relative, needle, label] of forbidden) {
  if (read(relative).includes(needle)) failures.push(`${label}: found ${JSON.stringify(needle)} in ${relative}`);
}

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(target) : [target];
  });
}

const appRoot = path.join(frontendRoot, "src", "app");
const pages = walk(appRoot).filter((file) => file.endsWith(`${path.sep}page.tsx`));
const pageLocalDialogs = pages.filter((file) => {
  const source = fs.readFileSync(file, "utf8");
  return source.includes('role="dialog"') && source.includes("fixed inset-0");
}).map((file) => path.relative(frontendRoot, file));
const specializedDirectDrawer = path.join("src", "app", "direct", "page.tsx");
const unsupportedPageDialogs = pageLocalDialogs.filter((file) => file !== specializedDirectDrawer);

notes.push(`Routes inspected statically: ${pages.length}`);
notes.push(`Shared-overlay exceptions: ${pageLocalDialogs.length}`);
for (const file of pageLocalDialogs) notes.push(`  - ${file}`);
if (unsupportedPageDialogs.length) {
  failures.push(`unsupported page-local fixed dialogs: ${unsupportedPageDialogs.join(", ")}`);
}

console.log("Mobile UI static regression");
for (const note of notes) console.log(note);
if (failures.length) {
  console.error("\nFAILED");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("PASS: exhaustive routes, shared mobile primitives, navigation, filters, forms and bounded overlays satisfy the contract.");
