/**
 * Clinovian — inquiry-flow browser acceptance tests.
 *
 * Loads the real contact.html into jsdom, executes the real main.js, and drives
 * the form the way a user would. Nothing is stubbed except fetch(), which is
 * mocked so no request ever leaves the machine.
 *
 * Usage:  node scripts/acceptance/inquiry-flow.js [repo-root]
 * Requires jsdom:  npm install --no-save jsdom
 */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const ROOT = process.argv[2] || path.join(__dirname, "..", "..");
let pass = 0, fail = 0;
const failures = [];

function check(cond, label, detail) {
  if (cond) { pass++; console.log(`  ok    ${label}`); }
  else {
    fail++; failures.push(label);
    console.log(`  FAIL  ${label}${detail ? "\n          " + detail : ""}`);
  }
}

function section(t) { console.log(`\n${"=".repeat(70)}\n${t}\n${"=".repeat(70)}`); }

/** Build a fresh DOM with main.js executed and fetch() mocked. */
function boot(page, { search = "", fetchImpl } = {}) {
  const html = fs.readFileSync(path.join(ROOT, page), "utf8");
  const dom = new JSDOM(html, {
    url: "https://clinovian.com/" + page + search,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const w = dom.window;

  // Minimal APIs main.js may touch that jsdom lacks.
  w.matchMedia = w.matchMedia || (q => ({
    matches: false, media: q, addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {},
  }));
  w.scrollTo = () => {};
  w.HTMLElement.prototype.scrollIntoView = function () {};

  const calls = [];
  w.fetch = (url, opts) => {
    calls.push({ url, opts });
    return fetchImpl ? fetchImpl(url, opts, calls.length)
                     : Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
  };
  w.__fetchCalls = calls;

  const js = fs.readFileSync(path.join(ROOT, "main.js"), "utf8");
  w.eval(js);
  w.document.dispatchEvent(new w.Event("DOMContentLoaded", { bubbles: true }));
  return { dom, w, d: w.document, calls };
}

const tick = (w, n = 6) =>
  new Promise(r => { let i = 0; const s = () => (++i >= n ? r() : w.setTimeout(s, 0)); s(); });

/** Fill every required control in the currently active flow. */
function fillRequired(d) {
  d.querySelectorAll("input, textarea, select").forEach(el => {
    if (el.disabled || el.type === "hidden") return;
    const need = el.required || el.getAttribute("required") !== null;
    if (!need) return;
    if (el.tagName === "SELECT") {
      const opt = Array.from(el.options).find(o => o.value);
      if (opt) el.value = opt.value;
    } else if (el.type === "checkbox") el.checked = true;
    else if (el.type === "email") el.value = "ops@example-health.org";
    else if (el.tagName === "TEXTAREA")
      el.value = "Commercial plan denied an inpatient stay on medical necessity. No identifiers included.";
    else el.value = "Example Health Partners";
  });
}

(async function run() {

  // ---------------------------------------------------------------- 3.1
  section("3.1  Form success confirmation (F03)");
  {
    const { w, d } = boot("contact.html");
    const status = d.getElementById("intake-status");
    const form = d.getElementById("intake-form");
    const shell = d.getElementById("intake-form-shell");

    check(!!status, "confirmation region exists");
    check(!!form && !form.contains(status), "confirmation region is OUTSIDE the form");
    check(status.getAttribute("aria-live") === "polite", "region is aria-live=polite");
    check(status.getAttribute("role") === "status", "region has role=status");
    check(!!shell, "#intake-form-shell exists (hide fields, not the form)");

    fillRequired(d);
    form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
    await tick(w);

    const visible = !status.hidden && status.style.display !== "none";
    check(visible, "after mocked 200 the confirmation is VISIBLE",
      `hidden=${status.hidden} display=${status.style.display}`);
    check(status.textContent.trim().length > 40, "confirmation carries a readable message");
    check(/business day/i.test(status.textContent), "confirmation states the response window");
    check(/no records should be sent|nothing has been committed/i.test(status.textContent),
      "confirmation states nothing is committed yet");
    const h = status.querySelector("h2");
    check(!!h && h.tabIndex === -1, "confirmation heading is focusable for focus move");
    check(shell.hidden === true, "editable fields hidden, form element retained");
    check(d.activeElement === h || status.contains(d.activeElement),
      "focus moved into the confirmation",
      `activeElement=<${d.activeElement && d.activeElement.tagName}>`);
  }

  // ---------------------------------------------------------------- 3.1b
  section("3.1b  Validation failure, server rejection, network failure, retry");
  {
    const { w, d } = boot("contact.html");
    const form = d.getElementById("intake-form");
    const status = d.getElementById("intake-status");
    form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
    await tick(w);
    check(w.__fetchCalls.length === 0, "empty form does NOT submit");
    const bad = d.querySelector('[aria-invalid="true"]');
    check(!!bad, "an invalid field is marked aria-invalid");
    check(!!bad && !!bad.getAttribute("aria-describedby"),
      "invalid field is bound to its message via aria-describedby");

    // correcting the field clears the error state
    if (bad) {
      bad.value = bad.type === "email" ? "ops@example-health.org" : "Example Health Partners";
      bad.dispatchEvent(new w.Event("input", { bubbles: true }));
      await tick(w, 3);
      check(bad.getAttribute("aria-invalid") !== "true",
        "error state clears when the field is corrected");
    }
  }
  {
    const { w, d } = boot("contact.html", {
      fetchImpl: () => Promise.resolve({
        ok: false, status: 422,
        json: () => Promise.resolve({ errors: [{ message: "Form rejected the submission." }] }),
      }),
    });
    const form = d.getElementById("intake-form");
    const status = d.getElementById("intake-status");
    const shell = d.getElementById("intake-form-shell");
    fillRequired(d);
    form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
    await tick(w);
    check(/rejected|try again/i.test(status.textContent), "server rejection surfaces a message");
    check(shell.hidden !== true, "server rejection leaves the fields editable for retry");
    const btn = form.querySelector('button[type="submit"]');
    check(btn && btn.disabled === false, "submit button re-enabled after rejection");
  }
  {
    const { w, d } = boot("contact.html", { fetchImpl: () => Promise.reject(new Error("offline")) });
    const form = d.getElementById("intake-form");
    const status = d.getElementById("intake-status");
    fillRequired(d);
    form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
    await tick(w);
    check(/contact@clinovian\.com/i.test(status.textContent),
      "network failure offers an email fallback");
    check(/do not include patient names|identifier/i.test(status.textContent),
      "network fallback RETAINS the no-PHI instruction");
    const btn = form.querySelector('button[type="submit"]');
    check(btn && btn.disabled === false, "submit button re-enabled after network failure");
  }
  {
    // duplicate clicks must not double-submit
    let resolve;
    const gate = new Promise(r => { resolve = r; });
    const { w, d } = boot("contact.html", {
      fetchImpl: () => gate.then(() => ({ ok: true, status: 200, json: () => Promise.resolve({}) })),
    });
    const form = d.getElementById("intake-form");
    fillRequired(d);
    form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
    await tick(w, 2);
    form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
    await tick(w, 2);
    check(w.__fetchCalls.length === 1,
      "duplicate submit does not fire a second request",
      `fetch calls=${w.__fetchCalls.length}`);
    resolve(); await tick(w);
  }

  // ---------------------------------------------------------------- 3.2
  section("3.2  Service preselection from every CTA (F07)");
  {
    const contact = fs.readFileSync(path.join(ROOT, "contact.html"), "utf8");
    const ctas = new Map();
    for (const f of fs.readdirSync(ROOT).filter(x => x.endsWith(".html"))) {
      const src = fs.readFileSync(path.join(ROOT, f), "utf8");
      for (const m of src.matchAll(/contact\.html\?service=([^"'>\s&#]+)/g)) {
        if (!ctas.has(decodeURIComponent(m[1]))) ctas.set(decodeURIComponent(m[1]), f);
      }
    }
    console.log(`  (${ctas.size} distinct service values across the site)`);
    let bad = 0;
    for (const [val, origin] of ctas) {
      const { d } = boot("contact.html", { search: "?service=" + encodeURIComponent(val) });
      const sel = d.querySelector('[name="service_interested_in"]');
      const chosen = sel && sel.value;
      const ok = chosen && chosen !== "" &&
        (chosen === val || (sel.selectedOptions[0] &&
          sel.selectedOptions[0].getAttribute("data-service-id") === val));
      if (!ok) { bad++; console.log(`  FAIL  '${val}' (from ${origin}) -> selected '${chosen}'`); }
    }
    check(bad === 0, `all ${ctas.size} service CTAs preselect their intended option`);

    // the ten that were broken in the audit
    const TEN = ["behavioral-health-denial-support", "cardiology-denial-support",
      "home-health-denial-escalation", "irf-denial-escalation", "ltach-denial-escalation",
      "neurology-denial-support", "oncology-denial-support", "orthopedic-denial-support",
      "recurring-clinical-review-capacity", "snf-denial-escalation"];
    let miss = 0;
    for (const page of TEN) {
      const src = fs.readFileSync(path.join(ROOT, page + ".html"), "utf8");
      const m = src.match(/contact\.html\?service=([^"'>\s&#]+)/);
      if (!m) { miss++; console.log(`  FAIL  ${page}.html has no service CTA`); continue; }
      const val = decodeURIComponent(m[1]);
      const { d } = boot("contact.html", { search: "?service=" + encodeURIComponent(val) });
      const sel = d.querySelector('[name="service_interested_in"]');
      if (!sel || !sel.value) { miss++; console.log(`  FAIL  ${page}.html -> '${val}' selects nothing`); }
    }
    check(miss === 0, "the ten originally-broken landing pages all route correctly");
  }

  // ---------------------------------------------------------------- 3.3
  section("3.3  Menu dismissal and ARIA state (F08)");
  {
    const { w, d } = boot("index.html");
    const btn = d.querySelector(".nav-dd-toggle[aria-expanded]");
    const item = btn && btn.closest(".nav-item");
    check(!!btn, "a dropdown toggle with aria-expanded exists");
    if (btn) {
      btn.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
      await tick(w, 3);
      check(btn.getAttribute("aria-expanded") === "true", "click opens: aria-expanded=true");
      check(item.classList.contains("open"), "click opens: .open class applied");

      btn.focus();
      d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      await tick(w, 3);
      check(btn.getAttribute("aria-expanded") === "false", "Escape sets aria-expanded=false");
      check(!item.classList.contains("open"), "Escape removes .open (visual state agrees)");
      check(d.activeElement === btn, "Escape leaves focus on the toggle (no focus jump)");
    }
    const css = fs.readFileSync(path.join(ROOT, "style.css"), "utf8");
    const hover = [...css.matchAll(/([^\n{}]*dropdown[^\n{}]*)\{([^}]*)\}/g)]
      .filter(m => /display:\s*block/.test(m[2]) && /(:hover|:focus-within)/.test(m[1]));
    check(hover.length === 0, "no CSS rule opens a dropdown on hover/focus-within",
      hover.map(h => h[1].trim()).join(" | "));
  }

  // ---------------------------------------------------------------- 3.4
  section("3.4  Conditional fields never serialise stale values (F11)");
  {
    const { w, d } = boot("contact.html");
    const sel = d.querySelector('[name="service_interested_in"]');
    const idr = d.getElementById("idr-intake-fields");
    check(idr && idr.tagName === "FIELDSET", "conditional group is a <fieldset>");

    // pick the IDR flow, fill one of its fields, then switch away
    const caseRadio = d.querySelector('input[name="inquiry_mode"][value="case"]');
    check(!!caseRadio, "case-fit mode is separate from general business inquiry");
    const idrOpt = Array.from(sel.options).find(o => /idr/i.test(o.value + o.textContent));
    if (idrOpt && caseRadio) {
      caseRadio.checked = true;
      caseRadio.dispatchEvent(new w.Event("change", { bubbles: true }));
      sel.value = idrOpt.value;
      sel.dispatchEvent(new w.Event("change", { bubbles: true }));
      await tick(w, 3);
      check(idr.disabled === false, "IDR group enabled when the IDR service is selected");
      const f = idr.querySelector("input, textarea");
      if (f) f.value = "STALE-VALUE-12345";

      const other = Array.from(sel.options).find(o => o.value && o.value !== idrOpt.value);
      sel.value = other.value;
      sel.dispatchEvent(new w.Event("change", { bubbles: true }));
      await tick(w, 3);
      check(idr.disabled === true, "IDR group DISABLED after switching away");

      const fd = new w.FormData(d.getElementById("intake-form"));
      const serialised = [...fd.entries()].map(([, v]) => String(v)).join("|");
      check(!serialised.includes("STALE-VALUE-12345"),
        "stale IDR value is NOT serialised into FormData");
    }
  }

  // ---------------------------------------------------------------- 3.5
  section("3.5  Progressive behaviour without JavaScript");
  {
    const contact = fs.readFileSync(path.join(ROOT, "contact.html"), "utf8");
    const form = contact.match(/<form id="intake-form"[^>]*>/);
    check(!!form && /action=/.test(form[0]), "form has a native action fallback");
    check(/<noscript/i.test(contact),
      "a <noscript> explanation exists for JS-dependent parts");
  }

  section("RESULT");
  console.log(`  ${pass} passed, ${fail} failed`);
  if (fail) { console.log("\n  failing:"); failures.forEach(f => console.log("   - " + f)); }
  process.exit(fail ? 1 : 0);
})();
