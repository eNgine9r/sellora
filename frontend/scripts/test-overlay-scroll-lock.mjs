// DOM-free regression of reference-counted modal scroll lock, including
// nested overlays, repeated release and preservation of pre-existing styles.
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = fs.readFileSync(path.join(root, "src/lib/overlay-scroll-lock.ts"), "utf8");
const js = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;

function harness({ initialInert = false, rootAttribute = null, ios = false } = {}) {
  const html = {
    clientWidth: 1260,
    style: { overflow: "auto", overscrollBehavior: "auto" },
    attributes: new Map(rootAttribute === null ? [] : [["data-sellora-scroll-locked", rootAttribute]]),
    getAttribute(key) { return this.attributes.get(key) ?? null; },
    setAttribute(key, value) { this.attributes.set(key, value); },
    removeAttribute(key) { this.attributes.delete(key); },
  };
  const body = {
    style: { overflow: "scroll", position: "relative", top: "8px", left: "4px", width: "88%", paddingRight: "9px", overscrollBehavior: "auto" },
  };
  const app = { inert: initialInert };
  const previousBody = { ...body.style };
  const previousHtml = { ...html.style };
  const scrollToCalls = [];
  const window = {
    innerWidth: 1280, scrollX: 25, scrollY: 347,
    scrollTo(x, y) { scrollToCalls.push([x, y]); this.scrollX=x; this.scrollY=y; },
  };
  const document = { documentElement: html, body, querySelector(selector) { assert.equal(selector, "[data-protected-shell-grid]"); return app; } };
  const exported = {};
  vm.runInNewContext(js, { exports: exported, document, window, navigator: { userAgent: ios ? "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit" : "Mozilla/5.0 Chrome/130", platform: ios ? "iPhone" : "Linux", maxTouchPoints: ios ? 5 : 0 }, getComputedStyle: () => ({ paddingRight: "9px" }) });
  return { acquire: exported.acquireOverlayScrollLock, html, body, app, previousBody, previousHtml, window, scrollToCalls };
}

{
  const d = harness();
  const releaseFirst = d.acquire();
  const releaseSecond = d.acquire();
  assert.equal(d.html.getAttribute("data-sellora-scroll-locked"), "true");
  assert.equal(d.app.inert, false, "portal content must remain independently scrollable");
  assert.equal(d.body.style.position, "relative", "desktop keeps wheel scrolling within dialogs");
  assert.equal(d.body.style.paddingRight, "calc(9px + 20px)");
  releaseFirst();
  assert.equal(d.html.style.overflow, "hidden", "closing an inner overlay must keep the outer lock");
  assert.equal(d.scrollToCalls.length, 0);
  releaseFirst();
  assert.equal(d.html.style.overflow, "hidden", "cleanup must be idempotent");
  releaseSecond();
  assert.deepEqual(d.body.style, d.previousBody);
  assert.deepEqual(d.html.style, d.previousHtml);
  assert.equal(d.html.getAttribute("data-sellora-scroll-locked"), null);
  assert.equal(d.app.inert, false);
  assert.deepEqual(d.scrollToCalls, [[25, 347]], "scroll position must be restored once");
  const again=d.acquire();
  again();
  assert.deepEqual(d.scrollToCalls, [[25,347],[25,347]]);
}
{
  const d=harness();
  const release=d.acquire({forceFixedBody:true});
  assert.equal(d.body.style.position, "fixed", "hamburger needs fixed body on mobile Chromium");
  assert.equal(d.body.style.top,"-347px");
  release();
  assert.deepEqual(d.body.style,d.previousBody);
  assert.deepEqual(d.scrollToCalls,[[25,347]]);
}
{
  const d = harness({ ios: true });
  const release=d.acquire();
  assert.equal(d.body.style.position, "fixed", "iOS keeps the fixed-body fallback");
  assert.equal(d.body.style.top, "-347px");
  release();
  assert.deepEqual(d.body.style, d.previousBody);
}
{
  const d = harness({ initialInert: true, rootAttribute: "prior" });
  const release=d.acquire();
  release();
  assert.equal(d.app.inert, true, "keep an earlier inert state");
  assert.equal(d.html.getAttribute("data-sellora-scroll-locked"), "prior", "restore prior attribute value");
}
console.log("OVERLAY_SCROLL_LOCK_NESTED_QA=PASS");
