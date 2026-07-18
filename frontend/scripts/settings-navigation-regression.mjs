import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const settingsPage = readFileSync(new URL("../src/app/settings/page.tsx", import.meta.url), "utf8");
const englishMessages = JSON.parse(readFileSync(new URL("../src/i18n/messages/en.json", import.meta.url), "utf8"));
assert.match(settingsPage, /href: "\/settings\/import"/, "Settings page must link to Import Center");
assert.match(settingsPage, /href: "\/settings\/integrations"/, "Settings page must link to Integrations");
assert.match(settingsPage, /settings\.cards\.integrationsTitle/, "Settings page must expose the integrations shortcut");

const integrationsPage = readFileSync(new URL("../src/app/settings/integrations/page.tsx", import.meta.url), "utf8");
assert.match(integrationsPage, /<NovaPoshtaSettingsCard\s+workspaceId=\{workspaceId\}/, "Integrations page must pass workspace context to settings card");

const settingsCard = readFileSync(new URL("../src/features/integrations/components/nova-poshta-settings-card.tsx", import.meta.url), "utf8");
assert.equal(englishMessages.novaPoshta.senderContactRef, "Sender contact person ref", "Sender settings must use clearer contact-person label");
assert.match(settingsCard, /novaPoshta\.senderContactRef/, "Sender settings must render the localized contact-person label");
assert.match(settingsCard, /CitySearchSelect/, "Sender settings must support city search");
assert.match(settingsCard, /WarehouseSearchSelect/, "Sender settings must support warehouse search");
