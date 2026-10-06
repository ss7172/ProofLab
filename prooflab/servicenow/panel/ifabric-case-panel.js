/*
 * iFabric ProofLab - ServiceNow evidence-chain panel. Framework-free, no dependencies.
 *
 *   IFabricCasePanel.render(element, caseOrCases)     draw one case or a list (schema ifabric.servicenow.case/v1)
 *   IFabricCasePanel.poll(element, url, everyMs)      fetch url (JSON case or list) on a timer; returns stop()
 *   <div data-ifabric-cases-src="cases.json" data-ifabric-poll-ms="10000"></div>   auto-start, no inline script
 *
 * Every value is written with textContent: incident text is untrusted (anyone with
 * access can edit a ServiceNow note), so nothing from the data is parsed as HTML.
 * Links are only rendered for http(s) URLs.
 */
(function (global) {
  'use strict';

  var SCHEMA = 'ifabric.servicenow.case/v1';
  // Field groups mirror prooflab/servicenow/assurance_agent.py: facts are ground truth the
  // orchestrator verified; judged fields are Nemotron's; Model carries gateway provenance.
  var FACT_FIELDS = ['Finding ID', 'Control', 'Threshold version', 'Scope', 'Verdict', 'Next step', 'Owner',
    'State', 'Owner response'];
  var JUDGED_FIELDS = ['Measured vs limit', 'Evidence refs', 'Missing evidence'];
  var RUN_PROBLEMS = ['REFUSED', 'BLOCKED', 'FAILED', 'UNVERIFIED'];
  var STALE_AFTER_MS = 5 * 60 * 1000;  // pending this long after delivery = the agent did not write
  var TONE = {
    good: ['DELIVERED', 'RESPONDED', 'SATISFIED', 'ok', 'present', 'written'],
    warn: ['AWAITING_RESPONSE', 'pending', 'DRY_RUN', 'INDETERMINATE', 'ESCALATED', 'NOT_SENT',
           'OUTCOME_UNKNOWN', 'UNVERIFIED', 'no_incident', 'not_applicable'],
    bad: ['BREACHED', 'FAILED', 'NO_RESPONSE_OBSERVED', 'RESPONSE_UNKNOWN', 'NOT_DELIVERED',
          'unreachable', 'unknown', 'incomplete', 'REFUSED', 'BLOCKED', 'NO_ANALYSIS']
  };

  function toneOf(value) {
    for (var tone in TONE) {
      if (TONE[tone].indexOf(value) !== -1) { return tone; }
    }
    return 'neutral';
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined && text !== null) { node.textContent = String(text); }
    return node;
  }

  function badge(value, label) {
    var text = label || String(value || 'n/a').replace(/_/g, ' ');
    return el('span', 'ifab-badge ifab-tone-' + toneOf(value), text);
  }

  function safeUrl(value) {
    if (!value) { return null; }
    try {
      var url = new URL(String(value), global.location.href);
      return (url.protocol === 'https:' || url.protocol === 'http:') ? url.href : null;
    } catch (err) {
      return null;
    }
  }

  function link(href, text) {
    var url = safeUrl(href);
    if (!url) { return el('span', 'ifab-muted', text || 'not linked'); }
    var a = el('a', 'ifab-link', text || url);
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    return a;
  }

  function facts(pairs) {
    var dl = el('dl', 'ifab-facts');
    pairs.forEach(function (pair) {
      if (pair[1] === undefined || pair[1] === null || pair[1] === '') { return; }
      dl.appendChild(el('dt', null, pair[0]));
      var dd = el('dd');
      if (pair[1] instanceof Node) { dd.appendChild(pair[1]); } else { dd.textContent = String(pair[1]); }
      dl.appendChild(dd);
    });
    return dl;
  }

  function step(number, title, status, body) {
    var li = el('li', 'ifab-step ifab-tone-' + toneOf(status));
    var head = el('div', 'ifab-step-head');
    head.appendChild(el('span', 'ifab-step-num', number));
    head.appendChild(el('span', 'ifab-step-title', title));
    head.appendChild(badge(status));
    li.appendChild(head);
    if (body) { li.appendChild(body); }
    return li;
  }

  function evidenceList(refs) {
    if (!refs || !refs.length) { return el('span', 'ifab-muted', 'none attached'); }
    var ul = el('ul', 'ifab-refs');
    refs.forEach(function (ref) { ul.appendChild(el('li', 'ifab-code', ref)); });
    return ul;
  }

  function findingStep(c) {
    var f = c.finding || {};
    return step(1, 'Control finding (AWS)', f.verdict, facts([
      ['Summary', f.summary], ['Detected', f.detected_at], ['Evidence', evidenceList(f.evidence)]
    ]));
  }

  function deliveryStep(c) {
    var d = c.delivery || {}, sn = c.servicenow || {};
    var incident = sn.number ? link(sn.url, sn.number) : (d.number || null);
    return step(2, 'Incident raised in ServiceNow', d.state, facts([
      ['Incident', incident], ['Delivered', d.at], ['ServiceNow', sn.status === 'ok' ? null : sn.status],
      ['Error', sn.error]
    ]));
  }

  function ownerStep(c) {
    var sn = c.servicenow || {}, r = c.response || {};
    return step(3, 'Named owner and response', r.state, facts([
      ['Owner', sn.owner], ['Incident state', sn.state], ['Responded by', r.actor], ['Responded at', r.at],
      ['Silence counts after', r.cutoff], ['Last updated by', sn.updated_by]
    ]));
  }

  function runFacts(run) {
    return facts([['Last run', run.state + (run.at ? ' · ' + run.at : '')], ['Reason', run.reason],
      ['Backend', run.backend], ['Gateway action ids', (run.action_ids || []).filter(Boolean).join(', ')],
      ['Run record', run.evidence]]);
  }

  function group(title, fields, names) {
    var wrap = el('div', 'ifab-group');
    wrap.appendChild(el('div', 'ifab-group-title', title));
    wrap.appendChild(facts(names.map(function (key) { return [key, fields[key]]; })));
    return wrap;
  }

  function presentBody(a, run) {
    var wrap = el('div'), fields = a.fields || {};
    var flags = el('div', 'ifab-flags');
    flags.appendChild(badge(a.complete ? 'ok' : 'incomplete', a.complete ? 'all fields present' : 'missing: ' + (a.missing_fields || []).join(', ')));
    flags.appendChild(badge(a.finding_matches ? 'ok' : 'incomplete', a.finding_matches ? 'finding id matches' : 'finding id does not match'));
    if (a.facts_match !== undefined) {
      flags.appendChild(badge(a.facts_match ? 'ok' : 'incomplete', a.facts_match ? 'facts match the finding' : 'facts differ from the finding'));
    }
    if (a.verified !== undefined && a.verified !== null) {
      flags.appendChild(badge(a.verified ? 'ok' : 'incomplete', a.verified ? 'written by the agent (in run log)' : 'not in the agent\'s run log'));
    }
    wrap.appendChild(flags);
    if (a.verified === false) {  // not in our run log: never present it as checked fact or as Nemotron's output
      wrap.appendChild(group('Note text — not written by the agent (untrusted)', fields, FACT_FIELDS.concat(JUDGED_FIELDS)));
      wrap.appendChild(facts([['Claimed provenance', fields.Model]]));
    } else {
      wrap.appendChild(group('Checked against the finding', fields, FACT_FIELDS));
      wrap.appendChild(group("Nemotron's judgement", fields, JUDGED_FIELDS));
      wrap.appendChild(facts([['Provenance', fields.Model]]));
    }
    wrap.appendChild(el('p', 'ifab-muted', 'Written ' + (a.at || '?') + ' by ' + (a.author || '?') + ' (ServiceNow display time).'));
    if (RUN_PROBLEMS.indexOf(run.state) !== -1) {
      wrap.appendChild(el('p', 'ifab-error', 'A later run did not write a new note:'));
      wrap.appendChild(runFacts(run));
    }
    return wrap;
  }

  function isStale(c) {
    var a = c.agent_analysis || {}, delivered = Date.parse((c.delivery || {}).at || '');
    return a.status === 'pending' && !isNaN(delivered) && Date.now() - delivered > STALE_AFTER_MS;
  }

  function analysisBody(a, run, stale) {
    if (a.status === 'present') { return presentBody(a, run); }
    if (stale && RUN_PROBLEMS.indexOf(run.state) === -1) {
      var note = el('div');
      note.appendChild(el('p', 'ifab-error', 'The assurance agent did not write an analysis within 5 minutes of delivery.'));
      if (run.state && run.state !== 'NOT_RUN') { note.appendChild(runFacts(run)); }
      return note;
    }
    if (RUN_PROBLEMS.indexOf(run.state) !== -1) {
      var wrap = el('div');
      wrap.appendChild(el('p', 'ifab-error', 'The assurance agent ran but no note was written.'));
      wrap.appendChild(runFacts(run));
      return wrap;
    }
    if (a.status === 'pending') {
      return el('p', 'ifab-muted', 'Waiting for the Nemotron assurance agent (usually under a minute after the incident is raised).');
    }
    return el('p', 'ifab-muted', a.status === 'not_applicable' ? 'No incident yet.' : 'Could not read the incident notes.');
  }

  function trusted(a) {
    return a.complete && a.finding_matches && a.facts_match !== false && a.verified !== false;
  }

  function analysisStep(c) {
    var a = c.agent_analysis || {status: 'unknown'}, run = c.agent_run || {state: 'NOT_RUN'};
    var status = a.status;
    if (a.status === 'present') { status = trusted(a) ? 'present' : 'incomplete'; }
    else if (RUN_PROBLEMS.indexOf(run.state) !== -1) { status = run.state; }
    var stale = isStale(c);
    if (stale && status === 'pending') { status = 'NO_ANALYSIS'; }
    return step(4, 'Assurance Agent analysis (Nemotron)', status, analysisBody(a, run, stale));
  }

  function aictStep(c) {
    var links = c.links || {};
    var li = step(5, 'AI Control Tower', links.aict ? 'ok' : 'not_applicable',
      facts([['Inventory', link(links.aict, 'AICT inventory entry')]]));  // a link, not a trace (gap A3)
    li.querySelector('.ifab-badge').textContent = links.aict ? 'linked' : 'not linked';
    return li;
  }

  // ------------------------------------------------------------ assurance analysis (5 sections)
  var CHECK_GLYPH = {pass: '✓', fail: '✕', unknown: '?'};
  var SOURCE_LABEL = {gateway: 'Gateway', agent: 'Agent', control: 'Control', servicenow: 'ServiceNow',
    owner: 'Owner', assurance_agent: 'Assurance Agent'};

  function shortTime(iso) {
    var m = /T(\d{2}:\d{2}:\d{2})/.exec(iso || '');
    return m ? m[1] + 'Z' : (iso || 'time not recorded');
  }

  // Trace decisions come from many sources (evaluator, log, agent), so fall back to keywords.
  function decisionBadge(decision) {
    var text = String(decision).replace(/_/g, ' '), tone = toneOf(decision);
    if (tone === 'neutral') {
      tone = /refus|deny|denied|block|fail|breach/i.test(text) ? 'bad'
        : (/allow|written|pass|deliver|respond|skipped/i.test(text) ? 'good' : 'neutral');
    }
    return el('span', 'ifab-badge ifab-tone-' + tone, text);
  }

  function plural(n, word) { return n + ' ' + word + (n === 1 ? '' : 's'); }

  function pill(tone, text) { return el('span', 'ifab-pill ifab-tone-' + tone, text); }

  function summaryPills(c) {
    var row = el('div', 'ifab-pills');
    var pol = c.policy_alignment, out = c.outcome_validation, mv = c.movement;
    if (pol) {
      var failed = pol.checks.some(function (k) { return k.status === 'fail'; });
      row.appendChild(pill(failed ? 'bad' : (pol.passed === pol.total ? 'good' : 'warn'), 'Policy ' + pol.passed + '/' + pol.total));
    }
    if (out) {
      row.appendChild(pill({validated: 'good', failed: 'bad'}[out.status] || 'warn', 'Outcome ' + out.status));
    }
    if (mv) {
      row.appendChild(pill(mv.steps.length ? 'neutral' : 'warn',
        mv.steps.length ? plural(mv.agents.length, 'agent') + ' · ' + plural(mv.gateway_crossings, 'gateway crossing') : 'Agent path not provided'));
    }
    return row;
  }

  function checklist(checks) {
    var ul = el('ul', 'ifab-checks');
    (checks || []).forEach(function (k) {
      var li = el('li', 'ifab-check ifab-check-' + k.status);
      var glyph = el('span', 'ifab-glyph', CHECK_GLYPH[k.status] || '?');
      glyph.setAttribute('aria-hidden', 'true');
      li.appendChild(glyph);
      var body = el('div', 'ifab-check-body');
      var head = el('div', 'ifab-check-head');
      head.appendChild(el('span', 'ifab-check-id', k.id));
      head.appendChild(el('span', 'ifab-check-label', k.label));
      head.appendChild(el('span', 'ifab-sr', k.status));
      body.appendChild(head);
      if (k.detail) { body.appendChild(el('div', 'ifab-muted', k.detail)); }
      li.appendChild(body);
      ul.appendChild(li);
    });
    return ul;
  }

  function section(title, summaryText, tone, open, content) {
    var d = el('details', 'ifab-sec');
    if (open) { d.open = true; }
    var s = el('summary', 'ifab-sec-head');
    s.appendChild(el('span', 'ifab-sec-title', title));
    if (summaryText) { s.appendChild(pill(tone || 'neutral', summaryText)); }
    d.appendChild(s);
    var body = el('div', 'ifab-sec-body');
    body.appendChild(content);
    d.appendChild(body);
    return d;
  }

  function flowDiagram(mv) {
    var zoneOf = {};
    mv.steps.forEach(function (s) { if (!(s.actor in zoneOf)) { zoneOf[s.actor] = s.zone; } });
    var ol = el('ol', 'ifab-flow');
    ol.setAttribute('aria-label', 'Agent path');
    var prevZone = null;
    mv.path.forEach(function (actor) {
      var zone = zoneOf[actor] || 'other';
      var li = el('li', 'ifab-node ifab-zone-' + (/^(customer|it|network|gateway)$/.test(zone) ? zone : 'other'));
      if (prevZone === 'network' && zone === 'customer') {  // the route rule M1 forbids this hop
        li.classList.add('ifab-hop-broken');
        li.title = 'Direct network → customer hop: no gateway in between';
      }
      prevZone = zone;
      li.appendChild(el('span', 'ifab-node-name', actor.replace(/_/g, ' ')));
      li.appendChild(el('span', 'ifab-node-zone', zone === 'it' ? 'IT zone' : zone));
      if (li.classList.contains('ifab-hop-broken')) { li.appendChild(el('span', 'ifab-node-flag', '✕ no gateway before this hop')); }
      ol.appendChild(li);
    });
    return ol;
  }

  function stepsTable(steps) {
    var table = el('table', 'ifab-steps');
    var head = el('tr');
    ['Time (UTC)', 'Agent', 'Zone', 'Action', 'Decision', 'Record'].forEach(function (h) { head.appendChild(el('th', null, h)); });
    var thead = el('thead'); thead.appendChild(head); table.appendChild(thead);
    var tbody = el('tbody');
    steps.forEach(function (s) {
      var tr = el('tr');
      [shortTime(s.at), s.actor, s.zone, s.action, s.decision || '—', s.ref || '—'].forEach(function (v, i) {
        tr.appendChild(el('td', i === 5 ? 'ifab-code' : null, v));
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    return table;
  }

  function movementSection(c) {
    var mv = c.movement, wrap = el('div');
    if (!mv.steps.length) {
      wrap.appendChild(el('p', 'ifab-muted', 'The evaluator did not attach the agents\' trace to this finding, so movement checks are unknown (never assumed to pass).'));
    } else {
      wrap.appendChild(flowDiagram(mv));
      var all = el('details', 'ifab-sub');
      all.appendChild(el('summary', null, 'All ' + mv.steps.length + ' steps'));
      all.appendChild(stepsTable(mv.steps));
      wrap.appendChild(all);
    }
    wrap.appendChild(checklist(mv.checks));
    var route = mv.checks[0] || {};
    return section('Agent movement', mv.steps.length ? plural(mv.agents.length, 'agent') + ' · ' + plural(mv.gateway_crossings, 'gateway') : 'not provided',
      route.status === 'fail' ? 'bad' : (mv.steps.length ? 'good' : 'neutral'), true, wrap);
  }

  function traceSection(c) {
    var ol = el('ol', 'ifab-timeline');
    (c.decision_trace || []).forEach(function (e) {
      var li = el('li', 'ifab-event ifab-src-' + e.source);
      var time = el('time', 'ifab-event-time', shortTime(e.at));
      if (e.at) { time.setAttribute('datetime', e.at); time.title = e.at; }
      li.appendChild(time);
      var body = el('div', 'ifab-event-body');
      var head = el('div', 'ifab-event-head');
      head.appendChild(el('span', 'ifab-src-badge', SOURCE_LABEL[e.source] || e.source));
      if (e.decision) { head.appendChild(decisionBadge(e.decision)); }
      head.appendChild(el('span', 'ifab-event-actor', e.actor));
      body.appendChild(head);
      if (e.detail) { body.appendChild(el('div', 'ifab-muted', e.detail)); }
      if (e.ref) { body.appendChild(el('div', 'ifab-code ifab-muted', e.ref)); }
      li.appendChild(body);
      ol.appendChild(li);
    });
    return section('Decision trace', plural((c.decision_trace || []).length, 'decision'), 'neutral', true, ol);
  }

  function evidenceSection(c) {
    var wrap = el('div'), items = c.evidence || [];
    if (!items.length) { wrap.appendChild(el('p', 'ifab-error', 'No evidence records attached to this finding.')); }
    var ul = el('ul', 'ifab-evidence');
    items.forEach(function (item) {
      var li = el('li');
      li.appendChild(el('span', 'ifab-kind ifab-kind-' + item.kind.replace(/[^a-z0-9]/g, ''), item.kind));
      li.appendChild(el('span', 'ifab-code', item.ref));
      if (item.used_by_agent) { li.appendChild(el('span', 'ifab-cited', 'cited by the agent')); }
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    var run = c.agent_run || {};
    wrap.appendChild(facts([['Incident', (c.servicenow || {}).number ? link((c.links || {}).incident, c.servicenow.number) : null],
      ['Agent run record', run.evidence], ['Gateway action ids', (run.action_ids || []).filter(Boolean).join(', ')]]));
    var cited = items.filter(function (i) { return i.used_by_agent; }).length;
    return section('Evidence', plural(items.length, 'record') + ' · ' + cited + ' cited', items.length ? 'neutral' : 'bad', false, wrap);
  }

  function policySection(c) {
    var pol = c.policy_alignment;
    var failed = pol.checks.filter(function (k) { return k.status === 'fail'; }).length;
    var unknown = pol.checks.filter(function (k) { return k.status === 'unknown'; }).length;
    var text = pol.passed + '/' + pol.total + ' pass' + (failed ? ' · ' + failed + ' fail' : '') + (unknown ? ' · ' + unknown + ' unknown' : '');
    return section('Policy alignment', text, failed ? 'bad' : (unknown ? 'warn' : 'good'), false, checklist(pol.checks));
  }

  function outcomeSection(c) {
    var out = c.outcome_validation;
    return section('Outcome validation', out.status, {validated: 'good', failed: 'bad'}[out.status] || 'warn', false,
      checklist(out.checks));
  }

  function assuranceBlock(c) {
    var wrap = el('section', 'ifab-assurance');
    wrap.setAttribute('aria-label', 'Assurance analysis');
    var head = el('div', 'ifab-assurance-head');
    head.appendChild(el('h4', null, 'Assurance analysis'));
    head.appendChild(el('span', 'ifab-muted', 'Computed by our checks from the finding, the delivery log and the agent\'s run record. Unknown means not provided, never passed.'));
    wrap.appendChild(head);
    [movementSection, traceSection, evidenceSection, policySection, outcomeSection].forEach(function (make) { wrap.appendChild(make(c)); });
    // Stable keys let render() keep what the viewer opened or closed across refreshes.
    wrap.querySelectorAll('details').forEach(function (d) {
      var title = d.querySelector(':scope > summary .ifab-sec-title');
      d.setAttribute('data-ifab-key', c.finding_id + '|' + (title ? title.textContent : 'steps'));
    });
    return wrap;
  }

  function renderCase(c) {
    var card = el('article', 'ifab-card');
    if (!c || c.schema !== SCHEMA) {
      card.appendChild(el('p', 'ifab-error', 'Unsupported data: expected schema ' + SCHEMA));
      return card;
    }
    var f = c.finding || {};
    var header = el('header', 'ifab-card-head');
    header.appendChild(badge(f.verdict));
    header.appendChild(el('h3', 'ifab-title', [f.control_ref, f.control_id].join(' ') + '  ·  v=' + f.threshold_version + '  ·  ' + f.scope_kind + ' ' + f.scope_id));
    header.appendChild(el('div', 'ifab-code ifab-id', c.finding_id));
    if (c.policy_alignment) { header.appendChild(summaryPills(c)); }
    card.appendChild(header);
    var chain = el('ol', 'ifab-chain');
    [findingStep, deliveryStep, ownerStep, analysisStep, aictStep].forEach(function (make) { chain.appendChild(make(c)); });
    card.appendChild(chain);
    if (c.movement && c.policy_alignment && c.outcome_validation) { card.appendChild(assuranceBlock(c)); }
    card.appendChild(el('footer', 'ifab-muted', 'Read-only view generated ' + c.generated_at + ' from the ServiceNow Table API and the delivery log.'));
    return card;
  }

  function openState(container) {
    var state = {};
    container.querySelectorAll('details[data-ifab-key]').forEach(function (d) { state[d.getAttribute('data-ifab-key')] = d.open; });
    return state;
  }

  function render(container, data) {
    var cases = Array.isArray(data) ? data : [data];
    var remembered = openState(container);
    container.classList.add('ifab-root');
    container.replaceChildren.apply(container, cases.length ? cases.map(renderCase) : [el('p', 'ifab-muted', 'No findings yet.')]);
    container.querySelectorAll('details[data-ifab-key]').forEach(function (d) {
      var key = d.getAttribute('data-ifab-key');
      if (Object.prototype.hasOwnProperty.call(remembered, key)) { d.open = remembered[key]; }
    });
  }

  function setStatus(container, text, isError) {
    var bar = container.querySelector(':scope > .ifab-status') || el('div', 'ifab-status');
    bar.textContent = text;
    bar.classList.toggle('ifab-error', !!isError);
    container.prepend(bar);
  }

  function offerFilePicker(container) {
    var label = el('label', 'ifab-picker', 'Live data unavailable here. Load a saved case snapshot (.json): ');
    var input = el('input');
    input.type = 'file';
    input.accept = 'application/json,.json';
    input.multiple = true;
    input.addEventListener('change', function () {
      var reads = Array.prototype.map.call(input.files, function (file) { return file.text().then(JSON.parse); });
      Promise.all(reads).then(function (cases) { render(container, [].concat.apply([], cases)); })
        .catch(function () { setStatus(container, 'That file is not a case snapshot.', true); });
    });
    label.appendChild(input);
    container.replaceChildren(label);
  }

  function poll(container, url, everyMs) {
    var stopped = false, timer = null, everLoaded = false;
    function tick() {
      fetch(url, {cache: 'no-store'}).then(function (response) {
        if (!response.ok) { throw new Error('HTTP ' + response.status); }
        return response.json();
      }).then(function (data) {
        everLoaded = true;
        render(container, data);
        setStatus(container, 'Updated ' + new Date().toLocaleTimeString() + ' · refreshes every ' + Math.round(everyMs / 1000) + ' s');
      }).catch(function (err) {
        if (!everLoaded && global.location.protocol === 'file:') { offerFilePicker(container); stopped = true; return; }
        setStatus(container, 'Could not refresh (' + err.message + '); showing the last data received.', true);
      }).then(function () {
        if (!stopped) { timer = global.setTimeout(tick, everyMs); }
      });
    }
    tick();
    return function stop() { stopped = true; global.clearTimeout(timer); };
  }

  function autoStart() {
    document.querySelectorAll('[data-ifabric-cases-src]').forEach(function (node) {
      poll(node, node.getAttribute('data-ifabric-cases-src'), Number(node.getAttribute('data-ifabric-poll-ms')) || 10000);
    });
  }

  global.IFabricCasePanel = {render: render, poll: poll, schema: SCHEMA, version: '1'};
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', autoStart); } else { autoStart(); }
})(window);
