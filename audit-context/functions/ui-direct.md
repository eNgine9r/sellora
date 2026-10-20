## DirectPage / ConversationList / MessageThread in frontend/src/app/direct/page.tsx (L55-L350,L404-L582)

**Purpose:** Select Direct conversation, load messages/customer state/AI, permit customer/order progression and confirmed manager reply.

**Inputs & Assumptions:**
- Workspace/role from useAuth L57,L68-L69; trusted for UI only.
- Semi-trusted API data from direct services L70-L112. Types define conversation IDs/link IDs, profile status and message direction (types/direct.ts L6-L51).
- selectedId local with fallback to first API conversation L78-L81; URL requested ID validated by membership in fetched list L162-L168.
- Assumes reply text belongs to selected customer; nothing found establishing this on selection change (shared state L63; selection L214-L217).
- Assumes prepare outcome belongs to current text/conversation; nothing found in rendering associates or resets mutation result (L118,L297).

**Outputs & Effects:**
- Polls list2s/messages1.5s/customer2s/history3s and suggestion/status queries (L70-L112).
- Runs explicit analysis/prepare/send/profile/customer/history/read POST mutations (L114-L149).
- Selecting unread/customer/profile can also trigger automatic POST effects (L175-L203).
- Customer card links to existing wizard with customer and conversation IDs (L638-L650).

**Block-by-Block:**
- L70-L112: workspace query keys isolate cache observers; background refetch remains enabled. Do not infer duplicate HTTP calls from multiple same-key observers without measurement.
- L114-L149: send uses current selectedConversation.id, shared replyText and new idempotency UUID; success clears shared text and invalidates current-key data. Concurrent selection/request ownership is open.
- L154-L173: workspace change resets local selection/text/ref guards; suggestion auto-fills whenever text empty. Conversation change does not reset text.
- L175-L203: profile refresh, read mark and intent/customer ensure side effects guarded by local refs; canManage guards ensure only.
- L259-L310: one grid below lg, fixed three panels at lg. List and thread both rendered below lg.
- L425-L477: sort intent then unread then newest; search input no onChange, decorative labels no buttons/filter state. Renders entire sorted input array.
- L535-L579: message autoscroll on count/ID; profile/customer cards above timeline; draft textarea and prepare/send CTAs. Timeline prints raw direction enum L561; send copy includes English L576.
- L584-L659: prospect create → order create → existing linked order actions. Missing fields displayed; safe order creation via separate page.

**Cross-Function Dependencies:**
- services/direct.ts (source inspected L14-L57): thin apiRequest wrappers; mutate routes methodPOST and send Idempotency-Key. They do not scope draft ownership.
- services/api.ts (source inspected L80-L106,L109-L152): obtains stored token/workspace, timeout20s, serialized refresh on401; backend workspace enforcement outside this UI audit.
- DirectLiveProvider (source inspected L175-L207): intent IDs from recent events; selected ID separately determined by URL every500ms then fallbackfirst.
- DirectCustomerExtractionPanel (source inspected L66-L86,L121-L208): finds card with MutationObserver and portals fields; polling and manual conflict apply.
- Backend Direct methods: delegated domain audit, not audited in this UI record.

**Open Questions:**
- Can request completion after selecting another conversation clear or invalidate the wrong local draft? Need behavioral fixture.
- How should selected query, provider intent and extraction panel share one canonical conversation?
- Actual reply policy (messaging window, permissions, writes switch, ambiguous outcomes) must remain server enforced.
- API list size/pagination contract not checked; do not invent paginated payload.
