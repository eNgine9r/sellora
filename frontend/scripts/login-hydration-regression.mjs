import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const login = readFileSync("frontend/src/app/login/page.tsx", "utf8");

// A user can type or have credentials autofilled before React hydrates.
// The browser's current form values, not stale component state, are submitted.
assert.match(login, /new FormData\(form\)/, "login must read current DOM form values");
assert.match(login, /login\(email, password\)/, "login must submit validated credentials");
assert.match(login, /form\.checkValidity\(\)/, "native email and required validations must remain");
assert.match(login, /String\(data\.get\("password"\) \?\? ""\)/, "password must not be trimmed");
assert.doesNotMatch(login, /value=\{email\}|value=\{password\}/, "login credentials must not be controlled during hydration");
assert.match(login, /if \(isSubmitting\) return/, "double submits must be prevented");
assert.match(login, /InvalidCredentialsError/, "invalid-credentials error handling must remain");
console.log("Login pre-hydration DOM submission regression passed (7 checks).");
