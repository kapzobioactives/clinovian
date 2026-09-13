(() => {
  'use strict';

  document.documentElement.classList.remove('no-js');
  document.documentElement.classList.add('js');

  const slug = (location.pathname.split('/').pop() || 'index.html').replace(/\.html$/, '').replace(/[^a-z0-9-]/gi, '-').toLowerCase() || 'home';
  document.body.classList.add('page-' + slug);

  /* ------------------------------------------------------------------ *
   * F21 — privacy-conscious conversion instrumentation.
   * Emits a DOM CustomEvent and appends to a bounded in-page buffer.
   * Never carries free text, clinical narrative, identifiers or field
   * values: the payload is limited to an event name and a small set of
   * enumerated, non-clinical properties defined in ANALYTICS.md.
   * ------------------------------------------------------------------ */
  const EVENT_BUFFER_MAX = 50;
  window.clinovianEvents = window.clinovianEvents || [];
  const SAFE_KEYS = ['page', 'service_id', 'setting', 'specialty', 'mode', 'source', 'outcome', 'reason'];
  function track(name, props) {
    const payload = { event: String(name).slice(0, 60), page: slug, ts: Date.now() };
    if (props) {
      SAFE_KEYS.forEach(k => {
        if (props[k] == null) return;
        // enumerated, short, non-clinical values only
        payload[k] = String(props[k]).replace(/[^A-Za-z0-9 _.:/-]/g, '').slice(0, 64);
      });
    }
    if (window.clinovianEvents.length >= EVENT_BUFFER_MAX) window.clinovianEvents.shift();
    window.clinovianEvents.push(payload);
    try { document.dispatchEvent(new CustomEvent('clinovian:event', { detail: payload })); } catch (e) { /* no-op */ }
  }
  window.clinovianTrack = track;

  const nav = document.getElementById('nav');
  const drawer = document.getElementById('mobile-drawer');
  const drawerPanel = drawer ? drawer.querySelector('.mobile-drawer-panel') : null;
  const toggle = document.querySelector('.mobile-toggle');
  const closeBtn = drawer ? drawer.querySelector('.drawer-close') : null;
  let lastFocus = null;

  function setNavScrolled() {
    if (nav) nav.classList.toggle('scrolled', window.scrollY > 20);
  }
  setNavScrolled();
  window.addEventListener('scroll', setNavScrolled, { passive: true });

  function focusables() {
    if (!drawerPanel) return [];
    return Array.from(drawerPanel.querySelectorAll('a[href], button:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'))
      .filter(el => el.offsetParent !== null || el === closeBtn);
  }

  /* F08 / 9.2 — background content is made inert while the drawer is open, so
     the drawer is a real modal rather than a visual overlay with stray focus. */
  const backgroundRegions = () => Array.from(document.querySelectorAll('main, footer, .trust, #nav'));
  function setBackgroundInert(on) {
    backgroundRegions().forEach(el => {
      if (!el) return;
      if (on) { el.setAttribute('inert', ''); el.setAttribute('aria-hidden', 'true'); }
      else { el.removeAttribute('inert'); el.removeAttribute('aria-hidden'); }
    });
  }

  function openDrawer() {
    if (!drawer || !toggle) return;
    lastFocus = document.activeElement;
    drawer.style.display = 'block';
    drawer.setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
    toggle.setAttribute('aria-expanded', 'true');
    setBackgroundInert(true);
    requestAnimationFrame(() => {
      drawer.classList.add('open');
      (closeBtn || focusables()[0] || toggle).focus({ preventScroll: true });
    });
    track('nav_drawer_open');
  }

  function closeDrawer() {
    if (!drawer || !toggle) return;
    if (drawer.style.display !== 'block') return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('drawer-open');
    toggle.setAttribute('aria-expanded', 'false');
    setBackgroundInert(false);
    window.setTimeout(() => {
      drawer.style.display = 'none';
      if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus({ preventScroll: true });
    }, 220);
  }

  if (toggle) toggle.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (drawer) {
    drawer.addEventListener('click', event => {
      if (event.target === drawer) closeDrawer();
    });
    drawer.addEventListener('keydown', event => {
      if (event.key === 'Tab') {
        const items = focusables();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    });
  }

  /* ------------------------------------------------------------------ *
   * F08 — one authoritative dropdown visibility state.
   * Visibility is driven solely by the `.open` class on the .nav-item.
   * CSS no longer opens panels on :hover or :focus-within, so Escape can
   * genuinely dismiss a panel while the pointer and focus stay put
   * (WCAG 2.2 SC 1.4.13, dismissible hover/focus content). Pointer and
   * focus still open panels — through JS, which honours the dismissal.
   * ------------------------------------------------------------------ */
  const ddToggles = Array.from(document.querySelectorAll('.nav-dd-toggle'));
  const ddItems = ddToggles.map(btn => btn.closest('.nav-item')).filter(Boolean);
  let dismissed = null; // item dismissed by Escape; stays shut until pointer/focus leaves

  function setOpen(item, open) {
    if (!item) return;
    const btn = item.querySelector('.nav-dd-toggle');
    item.classList.toggle('open', !!open);
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeAllDropdowns(except) {
    ddItems.forEach(item => { if (item !== except) setOpen(item, false); });
  }

  ddToggles.forEach(btn => {
    const item = btn.closest('.nav-item');
    if (!item) return;
    btn.addEventListener('click', event => {
      event.stopPropagation();
      const isOpen = item.classList.contains('open');
      closeAllDropdowns();
      dismissed = null;
      setOpen(item, !isOpen);
      if (!isOpen) track('nav_dropdown_open');
    });
    item.addEventListener('mouseenter', () => {
      if (dismissed === item) return;
      closeAllDropdowns(item);
      setOpen(item, true);
    });
    item.addEventListener('mouseleave', () => {
      if (dismissed === item) dismissed = null;
      if (!item.contains(document.activeElement)) setOpen(item, false);
    });
    item.addEventListener('focusin', () => {
      if (dismissed === item) return;
      closeAllDropdowns(item);
      setOpen(item, true);
    });
    item.addEventListener('focusout', event => {
      if (!item.contains(event.relatedTarget)) {
        if (dismissed === item) dismissed = null;
        setOpen(item, false);
      }
    });
  });

  document.addEventListener('click', () => { closeAllDropdowns(); dismissed = null; });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const openItem = ddItems.find(item => item.classList.contains('open'));
    if (openItem) {
      // Dismiss without moving focus or the pointer; keep it shut until they leave.
      setOpen(openItem, false);
      dismissed = openItem;
      const btn = openItem.querySelector('.nav-dd-toggle');
      if (btn && !openItem.contains(document.activeElement)) btn.focus({ preventScroll: true });
      return;
    }
    closeDrawer();
  });

  const revealEls = Array.from(document.querySelectorAll('.reveal'));
  if ('IntersectionObserver' in window) {
    const ro = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('on');
          ro.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    revealEls.forEach(el => ro.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add('on'));
  }

  /* F21 — CTA instrumentation: records the destination service ID only, never
     link text the buyer typed or any field value. */
  document.addEventListener('click', event => {
    const a = event.target.closest && event.target.closest('a[href*="contact.html"]');
    if (!a) return;
    let sid = '';
    try { sid = new URL(a.getAttribute('href'), location.href).searchParams.get('service') || ''; } catch (e) { /* no-op */ }
    track('cta_click', { service_id: sid, source: slug });
  }, true);

  function wireContactForm() {
    const form = document.getElementById('intake-form');
    if (!form) return;

    const statusBox = document.getElementById('intake-status');       // F03: lives OUTSIDE the form
    const formShell = document.getElementById('intake-form-shell');
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalLabel = submitBtn ? submitBtn.textContent : '';
    const summary = form.querySelector('[name="case_summary"]');
    const reason = form.querySelector('[name="escalation_reason"]');
    const serviceSelect = form.querySelector('[name="service_interested_in"]');
    const idrFields = document.getElementById('idr-intake-fields');
    const denialFields = document.getElementById('denial-intake-fields');
    const caseFieldset = document.getElementById('case-fit-fields');
    const summaryLabel = document.getElementById('f-summary-label');
    const summaryHelp = document.getElementById('f-summary-help');
    const reasonLabel = document.getElementById('f-reason-label');
    const modeRadios = Array.from(form.querySelectorAll('input[name="inquiry_mode"]'));
    const errorSummary = document.getElementById('intake-error-summary');

    // Flags likely identifiers, not innocent words: full dates, ID-style keywords followed
    // by a value, letter+digit tokens, and long digit runs (SSN/MRN/phone length).
    const prohibitedPattern = /(\b\d{1,2}[\/\-.]\d{1,2}[\/\-.](?:\d{2}|\d{4})\b|\b(?:dob|date of birth|mrn|medical record(?: number| no\.?| #)?|member id|claim (?:number|no\.?|#)|subscriber id|policy number|account number)\b[\s:#.\-]{0,3}[A-Za-z0-9]|\b[A-Z]{2,}\d{5,}\b|\b\d{9,}\b|\b\d{3}[\-. ]\d{2}[\-. ]\d{4}\b|\b\(?\d{3}\)?[\-. ]\d{3}[\-. ]\d{4}\b)/i;

    function isIdrService(value) {
      return value === 'NSA/IDR Clinical Value Dossier' || value === '3-Dossier Federal IDR Evaluation';
    }
    function currentMode() {
      const checked = modeRadios.find(r => r.checked);
      return checked ? checked.value : 'business';
    }

    /* F11 — fields that are not part of the active flow are DISABLED, not merely
       hidden. A disabled control is omitted from FormData, so a stale value from
       a previously selected service can no longer be submitted. */
    function setGroupActive(group, active) {
      if (!group) return;
      group.hidden = !active;
      group.disabled = !active;
      group.querySelectorAll('input, select, textarea').forEach(el => {
        el.disabled = !active;
        if (!active) {
          el.required = false;
        }
      });
    }

    function updateIntakeFields() {
      if (!serviceSelect) return;
      const mode = currentMode();
      const caseMode = mode === 'case';
      const idr = caseMode && isIdrService(serviceSelect.value);

      setGroupActive(caseFieldset, caseMode);
      setGroupActive(idrFields, caseMode && idr);
      setGroupActive(denialFields, caseMode && !idr);

      if (caseMode && idr) {
        idrFields.querySelectorAll('[data-required-idr="true"]').forEach(el => { el.required = true; });
      }
      if (summary) summary.required = caseMode;

      if (summaryLabel) summaryLabel.textContent = idr
        ? 'De-identified dispute summary *'
        : 'De-identified case summary / denial rationale *';
      if (summary) summary.placeholder = idr
        ? 'Describe the dispute, service context, and existing submission need—without patient, claim, or portal identifiers.'
        : "What was denied, the payer's stated rationale, and the clinical picture—no patient name, DOB, MRN, or other identifiers.";
      if (summaryHelp) summaryHelp.textContent = idr
        ? 'Summarize the workflow need and clinical context. Do not paste claim numbers, patient details, or portal information.'
        : 'This is the field a physician reads first. Keep it de-identified and specific enough to assess fit.';
      if (reasonLabel) reasonLabel.textContent = idr ? 'Why your team is seeking physician review' : 'Why your team escalated this case';
      if (reason) reason.placeholder = idr
        ? 'What is missing or weak in the current clinical narrative or QA process?'
        : "What's making this one hard to resolve internally?";
    }

    /* F07 — stable service IDs are the routing key. Human-readable labels are
       still what the recipient sees, but they are no longer what the URL carries,
       so a wording change on a landing page can no longer silently break routing.
       `setting` and `specialty` are captured separately from the product. */
    function selectService() {
      if (!serviceSelect) return;
      const qs = new URLSearchParams(window.location.search);
      const requested = qs.get('service');
      const setting = qs.get('setting');
      const specialty = qs.get('specialty');
      let matched = '';

      if (requested) {
        const options = Array.from(serviceSelect.options);
        // 1. stable ID (current contract)
        let hit = options.find(o => o.dataset.serviceId === requested);
        // 2. exact label (legacy links and bookmarks)
        if (!hit) hit = options.find(o => o.value === requested);
        // 3. case-insensitive label, last resort
        if (!hit) hit = options.find(o => o.value.toLowerCase() === requested.toLowerCase());
        if (hit) {
          serviceSelect.value = hit.value;
          matched = hit.dataset.serviceId || hit.value;
        }
      }

      const hidSetting = form.querySelector('[name="routed_setting"]');
      const hidSpecialty = form.querySelector('[name="routed_specialty"]');
      const hidServiceId = form.querySelector('[name="routed_service_id"]');
      const clean = v => (v || '').replace(/[^a-z0-9-]/gi, '').slice(0, 48);
      if (hidSetting) hidSetting.value = clean(setting);
      if (hidSpecialty) hidSpecialty.value = clean(specialty);
      if (hidServiceId) hidServiceId.value = clean(matched);

      if (requested && !matched) {
        track('intake_route_miss', { service_id: requested, source: 'query' });
      } else if (matched) {
        track('intake_route_ok', { service_id: matched, setting: clean(setting), specialty: clean(specialty) });
      }
      // A case-specific CTA lands directly in the case-fit flow.
      if (matched && matched !== 'rcm-partnership' && matched !== 'recurring-capacity') {
        const caseRadio = modeRadios.find(r => r.value === 'case');
        if (caseRadio) caseRadio.checked = true;
      }
    }

    if (serviceSelect) {
      selectService();
      serviceSelect.addEventListener('change', updateIntakeFields);
    }
    modeRadios.forEach(r => r.addEventListener('change', () => {
      updateIntakeFields();
      track('intake_mode_change', { mode: currentMode() });
    }));
    updateIntakeFields();

    /* F03 — the status region is a sibling of the form, never a descendant, so a
       successful submission can hide the fields and still show the confirmation. */
    function showStatus(kind, message, heading) {
      if (!statusBox) return;
      statusBox.innerHTML = '';
      const box = document.createElement('div');
      box.className = kind === 'error' ? 'note warn' : 'note';
      if (heading) {
        const h = document.createElement('h2');
        h.textContent = heading;
        h.tabIndex = -1;
        h.style.cssText = "font-family:'Spectral',serif;font-size:22px;font-weight:600;margin-bottom:10px";
        box.appendChild(h);
      }
      const p = document.createElement('p');
      if (!heading) {
        const strong = document.createElement('strong');
        strong.textContent = kind === 'error' ? 'Could not send. ' : 'Sent. ';
        p.appendChild(strong);
      }
      p.appendChild(document.createTextNode(message));
      box.appendChild(p);
      statusBox.appendChild(box);
      statusBox.hidden = false;
      statusBox.style.display = 'block';
      if (kind === 'error') {
        statusBox.setAttribute('role', 'alert');
      } else {
        statusBox.setAttribute('role', 'status');
        const h = box.querySelector('h2');
        if (h) h.focus({ preventScroll: false });
      }
    }

    /* F08 / 8.4 — errors are bound to their field with aria-invalid and
       aria-describedby, and repeated in a summary the user can act on. */
    function clearErrors() {
      form.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
      form.querySelectorAll('[aria-invalid="true"]').forEach(el => el.removeAttribute('aria-invalid'));
      form.querySelectorAll('.field-error-msg').forEach(el => el.remove());
      if (errorSummary) { errorSummary.hidden = true; errorSummary.innerHTML = ''; }
    }

    function setError(el, message) {
      const field = el ? el.closest('.field') : null;
      if (field) field.classList.add('field-error');
      if (el) {
        el.setAttribute('aria-invalid', 'true');
        const id = el.id || ('fld-' + Math.random().toString(36).slice(2, 8));
        el.id = id;
        const msgId = id + '-err';
        if (!document.getElementById(msgId)) {
          const span = document.createElement('span');
          span.className = 'help field-error-msg';
          span.id = msgId;
          span.style.color = 'var(--red)';
          span.textContent = message;
          (field || el.parentNode).appendChild(span);
        }
        const described = (el.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
        if (described.indexOf(msgId) === -1) described.push(msgId);
        el.setAttribute('aria-describedby', described.join(' '));
      }
      if (errorSummary) {
        errorSummary.hidden = false;
        errorSummary.innerHTML = '';
        const h = document.createElement('p');
        h.innerHTML = '<strong>There is a problem with this form.</strong>';
        errorSummary.appendChild(h);
        const ul = document.createElement('ul');
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = '#' + (el ? el.id : '');
        a.textContent = message;
        a.addEventListener('click', ev => { ev.preventDefault(); if (el) el.focus(); });
        li.appendChild(a);
        ul.appendChild(li);
        errorSummary.appendChild(ul);
      }
      if (el && typeof el.focus === 'function') el.focus();
    }

    ['input', 'change'].forEach(evt => {
      form.addEventListener(evt, event => {
        const field = event.target.closest && event.target.closest('.field');
        if (field) field.classList.remove('field-error');
        if (event.target && event.target.getAttribute && event.target.getAttribute('aria-invalid') === 'true') {
          event.target.removeAttribute('aria-invalid');
        }
      });
    });

    let started = false;
    form.addEventListener('input', () => {
      if (!started) { started = true; track('intake_start', { mode: currentMode() }); }
    }, { once: false });

    form.addEventListener('submit', event => {
      event.preventDefault();
      if (statusBox) { statusBox.style.display = 'none'; statusBox.hidden = true; }
      clearErrors();

      // Scan every enabled text control in the active flow, not visible textareas only.
      const fieldsToCheck = Array.from(form.querySelectorAll('textarea, input[type="text"]'))
        .filter(el => !el.disabled && el.type !== 'hidden');
      for (const el of fieldsToCheck) {
        const match = prohibitedPattern.exec(el.value || '');
        if (match) {
          const fragment = String(match[0]).slice(0, 40);
          setError(el, 'This looks like it may contain an identifier: \u201C' + fragment + '\u201D. Please remove patient or claim-specific identifiers (dates of birth, MRN/claim/policy numbers, long digit strings) and resubmit with a de-identified summary. If this text is not an identifier, rephrase it — for example, write the year only instead of a full date.');
          track('intake_blocked_identifier_pattern', { mode: currentMode() });
          return;
        }
      }
      if (!form.checkValidity()) {
        const firstInvalid = form.querySelector(':invalid');
        if (firstInvalid) {
          setError(firstInvalid, firstInvalid.validationMessage || 'This field needs to be completed.');
        } else {
          form.reportValidity();
        }
        track('intake_validation_error', { mode: currentMode() });
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending…';
      }
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
        .then(res => {
          if (res.ok) {
            // Hide the editable fields only; the status region is outside the form.
            if (formShell) formShell.hidden = true; else form.style.display = 'none';
            showStatus('success',
              'Clinovian will reply to the email address you supplied within one business day, and will confirm service fit, the records required, turnaround and a fixed fee before any record is transferred. Nothing has been committed and no records should be sent yet. If you do not hear back, email contact@clinovian.com.',
              'Inquiry received');
            track('intake_success', { mode: currentMode() });
            return;
          }
          return res.json().catch(() => ({})).then(data => {
            const msg = data && data.errors && data.errors.length ? data.errors.map(er => er.message).join(', ') : 'Please try again, or email contact@clinovian.com directly.';
            showStatus('error', msg);
            track('intake_server_error', { outcome: String(res.status) });
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.textContent = originalLabel;
            }
          });
        })
        .catch(() => {
          showStatus('error', 'Please email contact@clinovian.com with your organisation, the workflow you are asking about, and a de-identified description. Do not include patient names, dates of birth, record or claim numbers, or any other identifier in that email.');
          track('intake_network_error');
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalLabel;
          }
        });
    });
  }
  wireContactForm();
})();
