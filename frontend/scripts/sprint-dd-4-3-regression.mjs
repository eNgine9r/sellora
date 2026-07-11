import { readFileSync } from 'node:fs';

const read = (path) => readFileSync(new URL(`../../${path}`, import.meta.url), 'utf8');
const failures = [];
const expect = (condition, message) => { if (!condition) failures.push(message); };

const crm = read('frontend/src/components/crm-workspace.tsx');
const appShell = read('frontend/src/components/app-shell.tsx');
const sidebar = read('frontend/src/components/app-sidebar.tsx');
const topbar = read('frontend/src/components/app-topbar.tsx');
const drawer = read('frontend/src/components/ui/overlay.tsx');

expect(crm.includes('layout?: "auto" | "five-balanced"'), 'CompactSummary must expose an explicit five-balanced layout API.');
expect(crm.includes('data-summary-layout={layout}'), 'CompactSummary must expose a static layout marker.');
expect(crm.includes('lg:grid-cols-6') && crm.includes('2xl:grid-cols-5'), 'Five-card layout must include balanced medium and five-column wide breakpoints.');
expect(crm.includes('lg:col-span-2') && crm.includes('lg:col-span-3'), 'Five-card layout must include explicit 3+2 card spans.');
expect(crm.includes('data-workspace-split-view') && crm.includes('clamp(360px,29vw,440px)'), 'WorkspaceSplitView must implement a clamped desktop side-panel column.');
expect(crm.includes('data-entity-side-panel="desktop"'), 'EntitySidePanel must expose a desktop aside marker.');
expect(crm.includes('<div className="lg:hidden"><Drawer'), 'EntitySidePanel must retain the mobile Drawer fallback.');
expect(!crm.includes('aria-modal="true"'), 'EntitySidePanel desktop implementation must stay non-modal.');
expect(drawer.includes('aria-modal="true"') && drawer.includes('backdrop-blur'), 'Generic Drawer must retain modal overlay semantics.');

const entityPages = [
  ['orders', 'frontend/src/app/orders/page.tsx', 'selectedOrder'],
  ['products', 'frontend/src/app/products/page.tsx', 'selectedProduct'],
  ['leads', 'frontend/src/app/leads/page.tsx', 'selectedLead'],
  ['customers', 'frontend/src/app/customers/page.tsx', 'selectedCustomer'],
];

for (const [name, path, selected] of entityPages) {
  const source = read(path);
  expect(source.includes('WorkspaceSplitView'), `/${name} must import/use WorkspaceSplitView.`);
  expect(source.includes(`<WorkspaceSplitView`) && source.includes(`panelOpen={Boolean(${selected})}`) && source.includes('panel={'), `/${name} must pass its detail panel into WorkspaceSplitView as a sibling column.`);
  expect(source.includes('EntitySidePanel'), `/${name} must render EntitySidePanel inside the split-view panel.`);
  expect(source.includes(`set${selected.replace('selected','Selected')}(null)`) || source.includes(`set${selected[0].toUpperCase()+selected.slice(1)}(null)`), `/${name} must clear selected entity state.`);
  const splitIndex = source.indexOf('<WorkspaceSplitView');
  const panelIndex = source.indexOf('<EntitySidePanel');
  expect(splitIndex !== -1 && panelIndex > splitIndex, `/${name} must not render EntitySidePanel before or outside WorkspaceSplitView.`);
}

const orders = read('frontend/src/app/orders/page.tsx');
const products = read('frontend/src/app/products/page.tsx');
expect(orders.includes('<CompactSummary layout="five-balanced"'), '/orders must explicitly opt into the five-card balanced summary layout.');
expect(products.includes('<CompactSummary layout="five-balanced"'), '/products must explicitly opt into the five-card balanced summary layout.');

const dashboard = read('frontend/src/app/dashboard/page.tsx');
for (const marker of ['data-dashboard-kpi-row', 'data-dashboard-operational-row', 'data-dashboard-analytics-row', 'data-dashboard-business-row', 'data-dashboard-operational-lists']) {
  expect(dashboard.includes(marker), `/dashboard missing required reference section marker ${marker}.`);
}
expect(!dashboard.includes('ownerContext.question'), 'Dashboard must not retain the oversized owner-context explanatory card in the main layout.');
expect(!dashboard.includes('xl:grid-cols-[0.9fr_1.1fr]'), 'Dashboard must not retain the old loose operational grid.');

expect(appShell.includes('data-protected-shell-grid'), 'AppShell must expose the unified desktop shell grid marker.');
expect(appShell.includes('--sidebar-width:220px') && appShell.includes('--topbar-height:72px'), 'AppShell must define shared sidebar/topbar dimensions.');
expect(appShell.includes('[grid-template-columns:var(--sidebar-width)_minmax(0,1fr)]') && appShell.includes('[grid-template-rows:var(--topbar-height)_minmax(0,1fr)]'), 'AppShell must use a two-row/two-column desktop grid.');
expect(appShell.includes('data-shell-brand-cell'), 'AppShell must render a dedicated brand header cell.');
expect(appShell.includes('<AppSidebar showBrand={false}'), 'Desktop Sidebar navigation must begin below the unified header row.');
expect(sidebar.includes('showBrand = true'), 'AppSidebar must preserve mobile/generic brand rendering while allowing desktop shell to hide it.');
expect(topbar.includes('data-shell-topbar') && topbar.includes('lg:h-[var(--topbar-height)]'), 'Topbar must use the shared topbar height variable.');
expect(topbar.includes('flex w-full min-w-0') && !topbar.includes('lg:max-w-[560px]') && !topbar.includes('xl:max-w-[680px]'), 'Topbar controls/search must span the full available desktop header width without old max-width caps.');
expect(sidebar.includes('lg:pt-5'), 'Sidebar navigation must keep a visible top offset below the unified header row.');
expect(orders.indexOf('<OrderTable') < orders.indexOf('<PaginationControls', orders.indexOf('<OrderTable')), '/orders primary pagination must render below the order table/list.');

if (failures.length) {
  console.error('Sprint Dd.4.3 regression guard failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Sprint Dd.4.3 regression guard passed.');
