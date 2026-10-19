## AppShell in frontend/src/components/app-shell.tsx (L53-L144)

**Purpose:** Wrap protected pages in authenticated workspace chrome, live Direct provider, desktop navigation and mobile navigation.

**Inputs & Assumptions:**
- children: trusted ReactNode from App Router.
- pathname: framework-provided route; protected set explicitly listed L17-L35.
- auth state/workspace: useAuth L56, client state for display; backend RBAC remains required.
- Mobile nav assumes five links match primary work; their current selection is hard-coded L37-L43. User's Direct-first intent is not represented there.
- Body scroll lock only follows mobileMenuOpen (L66-L69); more-sheet lock is delegated to BottomSheet.

**Outputs & Effects:**
- Redirects unauthenticated protected route to login (L62-L64).
- Public routes bypass shell; loading/redirect and no-workspace states explicit (L76-L78,L108).
- Mounts DirectLiveProvider for all protected content (L83,L142), which polls live summary and can request browser notifications separately.
- Logout clears via hook then navigates login (L71-L74).

**Block-by-Block:**
- L62-L78: auth redirect/effects run before main shell rendering. Client display gating established; server authorization is not established here.
- L83-L109: grid desktop chrome, sidebar220px, topbar72px, main constrained min-width0, content vertical scroll. Backend data and errors come from child/providers.
- L112-L123: six-cell floating mobile capsule, five fixed routes plus profile button, safe-area bottom. No Direct quick link exists in the current array.
- L125-L138: independent mobile sidebar with backdrop and profile/theme/language/logout footer.

**Cross-Function Dependencies:**
- AppSidebar (internal, source inspected): fifteen links L9-L25, aliases treated active L40.
- AppTopbar (internal, source inspected): global search has no handler L66-L69; createOrder navigates /orders L42.
- MobileMoreSheet (internal, source inspected): shared BottomSheet; create action delegates provided callback L37; Direct link L40-L42.
- DirectLiveProvider (internal, source inspected): live polling; mounts extraction portal on Direct L201-L207.
- useAuth (internal): session server authorization not audited by this UI task.

**Open Questions:**
- Measure actual overflow/focus behavior with synthetic API fixture at 375/390/1280/1440.
- Mobile drawer uses custom overlay rather than shared Drawer; keyboard/focus behavior not measured.
- Grouping navigation needs preserve all routes and analyst access; backend permission audit owns enforcement.
