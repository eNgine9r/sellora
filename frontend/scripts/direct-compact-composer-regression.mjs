import { readFileSync } from "node:fs";

const direct = readFileSync("frontend/src/app/direct/page.tsx", "utf8");
const css = readFileSync("frontend/src/app/globals.css", "utf8");
const shell = readFileSync("frontend/src/components/app-shell.tsx", "utf8");

const checks = [
  ["compact chat composer exists", direct.includes("data-direct-compact-composer") && direct.includes("data-direct-reply-input")],
  ["single small manual send action", direct.includes('aria-label="Надіслати повідомлення"') && direct.includes("data-direct-send") && direct.includes("onClick={onSend}")],
  ["send remains disabled without text or permissions", direct.includes("disabled={sendDisabled || !replyText.trim() || sendPending}")],
  ["prepare action remains independently available", direct.includes("data-direct-prepare") && direct.includes("onClick={onPrepare}")],
  ["manual-only AI disclosure retained", direct.includes("title={noAutoSend}") && direct.includes("AI-чернетки · лише вручну")],
  ["no duplicated long disclaimer", !direct.includes("Чернетка AI — не відправлено.")],
  ["technical message direction enums never rendered", !direct.includes("{message.direction} ·") && direct.includes("formatDirectMessageTime")],
  ["readable wrap and low-profile metadata", direct.includes("whitespace-pre-wrap break-words") && direct.includes('className={`mt-1 flex flex-wrap')],
  ["mobile tab bar hidden only in active chat", direct.includes('document.body.classList.toggle("direct-thread-open", isMobile && threadOpenOnMobile)') && css.includes("body.direct-thread-open .mobile-bottom-nav")],
  ["mobile thread reclaims viewport", css.includes("body.direct-thread-open .direct-mobile-thread") && shell.includes("data-shell-page-column")],
  ["iOS minimum input font size", direct.includes("px-2.5 py-2.5 text-base leading-6")],
  ["no keyboard auto-send shortcut", !direct.includes("onKeyDown={(event) => event.key === \"Enter\"")],
  ["send and preparation errors are visible", direct.includes("sendError ?") && direct.includes("prepareError ?")],
  ["old preview cleared as draft changes", direct.includes("prepareMutation.reset();") && direct.includes("sendMutation.reset();")],
  ["backend API flow unchanged", direct.includes("sendDirectReply(selectedConversation!.id, replyText, crypto.randomUUID())") && direct.includes("prepareDirectReply(selectedConversation!.id, replyText)")],
];
const failed = checks.filter(([, passed]) => !passed);
for (const [label, passed] of checks) console.log(`${passed ? "PASS" : "FAIL"} ${label}`);
if (failed.length) process.exit(1);
