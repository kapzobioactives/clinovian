(() => {
  'use strict';

  document.documentElement.classList.remove('no-js');
  document.documentElement.classList.add('js');

  const slug = (location.pathname.split('/').pop() || 'index.html').replace(/\.html$/, '').replace(/[^a-z0-9-]/gi, '-').toLowerCase() || 'home';
  document.body.classList.add('page-' + slug);

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

  function openDrawer() {
    if (!drawer || !toggle) return;
    lastFocus = document.activeElement;
    drawer.style.display = 'block';
    drawer.setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
    toggle.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => {
      drawer.classList.add('open');
      (closeBtn || focusables()[0] || toggle).focus({ preventScroll: true });
    });
  }

  function closeDrawer() {
    if (!drawer || !toggle) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('drawer-open');
    toggle.setAttribute('aria-expanded', 'false');
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

  const ddToggles = Array.from(document.querySelectorAll('.nav-dd-toggle'));
  function closeAllDropdowns(except) {
    ddToggles.forEach(btn => {
      if (btn !== except) btn.setAttribute('aria-expanded', 'false');
    });
  }
  ddToggles.forEach(btn => {
    btn.addEventListener('click', event => {
      event.stopPropagation();
      const isOpen = btn.getAttribute('aria-expanded') === 'true';
      closeAllDropdowns();
      btn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
    });
    const item = btn.closest('.nav-item');
    if (item) {
      item.addEventListener('mouseenter', () => closeAllDropdowns(btn));
    }
  });
  document.addEventListener('click', () => closeAllDropdowns());
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeAllDropdowns();
      closeDrawer();
    }
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

  function wireContactForm() {
    const form = document.getElementById('intake-form');
    if (!form) return;
    const statusBox = document.getElementById('intake-status');
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalLabel = submitBtn ? submitBtn.textContent : '';
    const summary = form.querySelector('[name="case_summary"]');
    const reason = form.querySelector('[name="escalation_reason"]');
    const serviceSelect = form.querySelector('[name="service_interested_in"]');
    const idrFields = document.getElementById('idr-intake-fields');
    const denialFields = document.getElementById('denial-intake-fields');
    const summaryLabel = document.getElementById('f-summary-label');
    const summaryHelp = document.getElementById('f-summary-help');
    const reasonLabel = document.getElementById('f-reason-label');

    // Flags likely identifiers, not innocent words: full dates, ID-style keywords followed
    // by a value, letter+digit tokens, and long digit runs (SSN/MRN/phone length).
    const prohibitedPattern = /(\b\d{1,2}[\/\-.]\d{1,2}[\/\-.](?:\d{2}|\d{4})\b|\b(?:dob|date of birth|mrn|medical record(?: number| no\.?| #)?|member id|claim (?:number|no\.?|#)|subscriber id|policy number|account number)\b[\s:#.\-]{0,3}[A-Za-z0-9]|\b[A-Z]{2,}\d{5,}\b|\b\d{9,}\b|\b\d{3}[\-. ]\d{2}[\-. ]\d{4}\b|\b\(?\d{3}\)?[\-. ]\d{3}[\-. ]\d{4}\b)/i;


    function isIdrService(value) {
      return value === 'NSA/IDR Clinical Value Dossier' || value === '3-Dossier Federal IDR Evaluation';
    }

    function updateIntakeFields() {
      if (!serviceSelect) return;
      const idr = isIdrService(serviceSelect.value);
      if (idrFields) idrFields.style.display = idr ? 'block' : 'none';
      if (denialFields) denialFields.style.display = idr ? 'none' : 'grid';
      form.querySelectorAll('[data-required-idr="true"]').forEach(el => {
        el.required = idr;
      });
      if (summaryLabel) summaryLabel.textContent = idr ? 'De-identified dispute summary *' : 'De-identified case summary / denial rationale *';
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

    if (serviceSelect) {
      const requestedService = new URLSearchParams(window.location.search).get('service');
      if (requestedService && Array.from(serviceSelect.options).some(option => option.value === requestedService)) {
        serviceSelect.value = requestedService;
      }
      serviceSelect.addEventListener('change', updateIntakeFields);
      updateIntakeFields();
    }

    function showStatus(kind, message) {
      if (!statusBox) return;
      statusBox.innerHTML = '';
      const box = document.createElement('div');
      box.className = kind === 'error' ? 'note warn' : 'note';
      const p = document.createElement('p');
      const strong = document.createElement('strong');
      strong.textContent = kind === 'error' ? 'Could not send. ' : 'Sent. ';
      p.appendChild(strong);
      p.appendChild(document.createTextNode(message));
      box.appendChild(p);
      statusBox.appendChild(box);
      statusBox.style.display = 'block';
      statusBox.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    }

    function setError(el, message) {
      const field = el ? el.closest('.field') : null;
      if (field) field.classList.add('field-error');
      showStatus('error', message);
      if (el && typeof el.focus === 'function') el.focus();
    }

    ['input', 'change'].forEach(evt => {
      form.addEventListener(evt, event => {
        const field = event.target.closest && event.target.closest('.field');
        if (field) field.classList.remove('field-error');
      });
    });

    form.addEventListener('submit', event => {
      event.preventDefault();
      if (statusBox) statusBox.style.display = 'none';
      form.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));

      const fieldsToCheck = Array.from(form.querySelectorAll('textarea')).filter(el => el.offsetParent !== null);
      for (const el of fieldsToCheck) {
        const match = prohibitedPattern.exec(el.value || '');
        if (match) {
          const fragment = String(match[0]).slice(0, 40);
          setError(el, 'This looks like it may contain an identifier: \u201C' + fragment + '\u201D. Please remove patient or claim-specific identifiers (dates of birth, MRN/claim/policy numbers, long digit strings) and resubmit with a de-identified summary. If this text is not an identifier, rephrase it — for example, write the year only instead of a full date.');
          return;
        }
      }
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending…';
      }
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
        .then(res => {
          if (res.ok) {
            form.style.display = 'none';
            showStatus('success', 'Your de-identified inquiry has been sent. Clinovian will respond within 24–48 hours at the email you provided.');
            return;
          }
          return res.json().catch(() => ({})).then(data => {
            const msg = data && data.errors && data.errors.length ? data.errors.map(er => er.message).join(', ') : 'Please try again, or email contact@clinovian.com directly.';
            showStatus('error', msg);
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.textContent = originalLabel;
            }
          });
        })
        .catch(() => {
          showStatus('error', 'Please email contact@clinovian.com directly with your case details.');
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalLabel;
          }
        });
    });
  }
  wireContactForm();
})();
