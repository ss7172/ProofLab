from pathlib import Path
import json, re, html, hashlib, zipfile

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / 'work/workshop-mapping'
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
BASE = 'https://catalog.us-east-1.prod.workshops.aws/event/dashboard/en-US/workshop'
tasks = json.loads((W/'workshop-task-plan.json').read_text())
mapping = json.loads((W/'workshop-map.json').read_text())
inventory = json.loads((OUT/'prooflab-component-inventory.json').read_text())
guide = []
for i, line in enumerate((W/'guide-index.txt').read_text().splitlines(), 1):
    suffix, title = line.split('|', 1)
    guide.append({'id':f'W{i:02}', 'title':title, 'url':BASE+suffix,
                  'state':'AUTHENTICATED_GUIDE_READ', 'read_date':'2026-10-04',
                  'runtime_verified':False})

assignment = {minor:t for t in tasks for minor in t['component_ids']}
minor_override = {
 'M01.1':('Customer experience agent','Documented customer-experience-agent on AgentCore Runtime. Earlier ServiceNow hosting assumption is superseded for this build.'),
 'M01.4':('Network digital twin','LF Connectivity MAVERIC; distinguish optional local RADP stack from provided network-twin Lambda. Not an NVIDIA model.'),
 'M01.7':('Customer-to-IT logical handoff','Earlier Gateway A label is a logical boundary. Discover actual HTTP/invocation interface; no separate gateway product presumed.'),
 'M01.8':('IT-to-network logical handoff','Earlier Gateway B label is a logical boundary. Discover actual HTTP/invocation interface; no separate gateway product presumed.'),
 'M01.12':('Available durable telemetry sources','Gateway/PDP logs, audit ledger and per-runtime CloudWatch spans/metrics; current collector trace export is discarded, not a working X-Ray pipeline.'),
 'M05.1':('Gateway and available telemetry readers','Read gateway/PDP logs and separately instrumented AgentCore per-runtime CloudWatch spans/metrics with full pagination and scope. The current shared collector trace pipeline discards spans; it is not an available durable OTEL/X-Ray source.'),
 'M08.1':('Accepted runtime/metric measurement manifest','Replaces earlier scenario/label manifest as the default C9 authority. Define runtimes, operations, metrics, dimensions, units and population.'),
 'M08.2':('Canonical metric mapping and comparison','Replaces earlier diagnostic outcome scorer as the default. Preserve Latency Average ms and Errors Sum count with exact windows; score-run.py is separate.'),
 'M08.3':('Frozen operational baseline builder','Closed comparable runtime/hour baseline with approved support, weighting, versions and zero-baseline rule.'),
 'M08.4':('Clock-hour scheduler and run membership','Expected UTC [start,end) runtime/hour windows; explicit many-run membership and source-finalization lag.'),
 'M08.6':('Operational drift calculator','Compute declared higher-is-worse latency change; use a predeclared absolute Errors-count rule for zero baseline or a validated aligned denominator for error rate. Preserve units/statistics and comparison boundaries.'),
 'M11.2':('Measured Nano investigator profile','Start approved nemotron-nano-9b; measured Nano30B alternative. Resolve live approval; no literal Lightning endpoint.'),
 'M11.10':('Nano Omni profile — CUT','Outside this text-only workshop. Retained ID for scope traceability, no implementation task required.'),
 'M11.11':('Ultra profile — CUT','Unavailable in this workshop. Retained ID for scope traceability, no implementation task required.'),
 'M16.3':('State, raw evidence and index adapters','Initial permissioned IDE host: SQLite facts/checkpoints/transactional outbox plus raw files; inspect persistence/restart behavior. Official team S3 is the permitted submission destination. Any distributed store requires a separately verified role and capability; component pods do not inherit IDE AWS access.'),
}
current_inventory=[]
parts=[(W/'claude-workshop-notes.txt').read_text()]
def section(title, body):
    parts.append('\n'+'='*78+'\n'+title+'\n'+'='*78+'\n\n'+body.strip()+'\n')

authority=(W/'claude-source-authority.txt').read_text()
authority=re.sub(r'\nREVIEW USE\n[\s\S]*$', '\nAll required context and task details are included in the chapters below; prior local files are optional historical references.\n', authority)
section('SOURCE AUTHORITY, COMPLETION REQUIREMENTS AND JUDGING', authority)
contract=(W/'claude-technical-contracts.txt').read_text()
contract=re.sub(r'Read alongside:[\s\S]*?\n1\. NON-NEGOTIABLE', 'The current technology map and task list are embedded below. Earlier walkthroughs are historical design references, superseded by the workshop corrections in this file.\n\n1. NON-NEGOTIABLE', contract)
section('IMPLEMENTATION CONTRACTS — INTERFACES, DATA, CONTROLS AND EDGE CASES', contract)
section('TWO-PERSON DELIVERY SEQUENCE', (W/'claude-delivery-plan.txt').read_text())

component_text=['The 16 groups and 123 minor IDs are logical responsibilities, not 123 deployables. Original IDs remain stable. Current names/roles below supersede historical candidate descriptions. DOCUMENTED means guide-supported, not deployed/tested by our team. Every task is initially NOT_IMPLEMENTED. A covered ID may be explicitly deferred/cut; mapping coverage is not completion.']
bymajor={m['component_id']:m for m in mapping}
for g in inventory['groups']:
    m=bymajor[g['id']]
    role = 'Operational runtime/hour latency and error drift using frozen comparable CloudWatch baselines.' if g['id']=='M08' else g['purpose']
    component_text += ['\n'+g['id']+' — '+g['name'], 'Purpose: '+role]
    newg={'id':g['id'],'name':g['name'],'purpose':role,'runtime_verified':False,'items':[]}
    for key,label in [('workshop_documented','Documented technologies/capabilities'),('architecture_adjustments','Current architecture adjustments'),('remaining_proof','Required runtime proof')]:
        component_text.append(label+':')
        component_text += ['  - '+x for x in m[key]]
        newg[key]=m[key]
    component_text.append('Minor components and responsible task:')
    for item in g['items']:
        name,purpose=minor_override.get(item['id'],(item['name'],item['purpose']))
        task=assignment[item['id']]
        disposition='CONDITIONAL_BONUS' if task['priority']!='CORE' else 'PLANNED_CORE'
        if g['id']=='M10': disposition='DEFERRED_UNSUPPORTED_INLINE_HOOK'
        if item['id'] in ['M11.10','M11.11']: disposition='CUT_CURRENT_EVENT'
        component_text.append(f"  {item['id']} {name} [{task['id']} | {disposition}]\n    {purpose}")
        newg['items'].append({'id':item['id'],'name':name,'purpose':purpose,'task_id':task['id'],'disposition':disposition,'runtime_verified':False})
    refs=[]
    for r in m['guide_refs']:
        s=r['guide_section']
        if s=='/platform-contract':s='/challenge-brief/platform-contract'
        u=BASE+s
        if u in {a['url'] for a in guide}:refs.append(u)
    component_text.append('Guide references: '+', '.join(dict.fromkeys(refs)))
    newg['source_urls']=list(dict.fromkeys(refs))
    current_inventory.append(newg)
section('COMPLETE COMPONENT INVENTORY AND WORKSHOP TECHNOLOGY MAP', '\n'.join(component_text))

records=[]
for name,desc in inventory['records']:
    if name=='Window':desc='Registered closed runtime/metric clock-hour assessment scope, baseline/config versions and linked run membership.'
    records.append(f'{name}: {desc}')
records += ['\nShared interfaces (our contract names; not promised vendor endpoints):']
records += [f'{name}: {desc} [{owner}]' for name,desc,owner in inventory['interfaces']]
records += ['The five methods evaluate/emit/callback/pull/query are adapter/query patterns. They are not a claim that the platform invokes all five at every enforcement point. The five architectural questions are separately stated in the source-authority chapter.']
section('CANONICAL RECORDS AND SHARED CONTRACT INDEX', '\n'.join(records))

task_text=['All 50 tasks below are NOT_IMPLEMENTED; platform/runtime verification is false. A=Person A, B=Person B, BOTH=paired. Dependencies refer to task IDs. CORE is our chosen three-control ambition; it does not mean the organizer mandates every task. Conditional bonuses cannot block the first completed control.']
for t in tasks:
    task_text += [f"\n{t['id']} — {t['title']}",f"Priority: {t['priority']} | Phase: {t['phase']} | Owner: {t['owner']} | Start dependencies: {', '.join(t['depends_on']) or 'none'}",'Components: '+', '.join(t['component_ids']), 'Technology: '+t['technology']]
    if t.get('conditional_gate'):task_text.append('Conditional acceptance gate: '+t['conditional_gate'])
    for milestone,deps in t.get('milestone_dependencies',{}).items():task_text.append('Milestone dependency — '+milestone+': '+', '.join(deps))
    for minor,disposition in t.get('component_disposition',{}).items():task_text.append('Component disposition — '+minor+': '+disposition)
    task_text.append('Platform asset aliases: '+', '.join(t.get('platform_asset_aliases',[])))
    task_text.append('Steps:')
    task_text += [f'  {i}. {s}' for i,s in enumerate(t['steps'],1)]
    task_text.append('Acceptance evidence:')
    task_text += ['  - '+s for s in t['done_when']]
    task_text += ['Risk: '+t['risk'],'Sources: '+', '.join(t.get('source_urls',[]))]
section('DETAILED TASK BACKLOG — OWNERS, DEPENDENCIES, STEPS AND ACCEPTANCE', '\n'.join(task_text))

index=['62 guide pages read. Source state refers to guide content, not runtime proof. Signed asset URLs, event invite codes and bearer resource URLs are excluded.']
index += [f"{p['id']} {p['title']}\n  {p['url']}" for p in guide]
index += ['\nOther sources interpreted: Trustworthy AI Hackathon developer masterclass Immersion Day slides.pdf (user supplied); Hackathon meeting transcript (1).txt (user supplied); prior ProofLab M01–M16 inventory and M01–M14 walkthrough/reviews (team design, not organizer authority). Physical PDF page references in the source chapter use PDF page count; printed slide numbers can differ.']
section('SOURCE INDEX AND EXTRACTION COVERAGE', '\n'.join(index))
section('EXTERNAL IMPLEMENTATION REFERENCE DIRECTORY', (W/'claude-reference-links.txt').read_text())
section('KICKOFF MESSAGE TO GIVE CLAUDE WITH THIS FILE', '''Act as our principal AI engineer and telecom assurance architect. Use the attached handoff as the current project context. We are a two-person team starting fresh in the supplied AWS Workshop Studio environment. Read the full file, preserve the stable M01–M16 and T01–T50 identifiers, and distinguish documented capabilities from untested assumptions.
Begin by inspecting the actual starter source and read-only runtime inventory using our authorized session. Report a compact mismatch list and update the decision/gap register. Plan the first real C16 pass/breach evidence slice while starting the declared hourly C9 baseline early. Extend the supplied code and operator paths. Keep requirements frozen before assessed runs. Do not build a new model gateway, custom crypto, unsupported model deployment or invented ServiceNow API.
Implement in small tested increments. For each task report what changed, why, actual validation evidence, remaining gaps and the next dependency. Maintain source identity, independent populations, many-to-many bindings without duplicate accounting, deterministic control arithmetic, and a bounded real Nemotron investigator with citations validated by host code. Credentials and bearer URLs must stay out of prompts, source and shareable exports.
Do not mark documented configuration or synthetic fixtures as live control completion. Deliver all six artifact categories, inspect the real submit script and verify the authorized official submission path when asked to execute it. Preserve unresolved organizer/access questions explicitly while continuing unaffected work. The target is reproducible evidence under the judge's two-minute limit; the one-minute model case target must be measured. Start with T01 and parallel policy/C9 planning, not another speculative architecture rewrite.''')

review_path=W/'handoff-review-summary.txt'
if review_path.exists():section('INDEPENDENT REVIEW AND DOCUMENT VALIDATION',review_path.read_text())
primary='\n'.join(parts)
# Historical shorthand must not create dead workshop links.
primary=primary.replace(BASE+'/platform-contract', BASE+'/challenge-brief/platform-contract')
(OUT/'claude-hackathon-context.txt').write_text(primary)
(OUT/'prooflab-workshop-tasks.json').write_text(json.dumps(tasks,indent=2)+'\n')
(OUT/'prooflab-workshop-components.json').write_text(json.dumps(current_inventory,indent=2)+'\n')
(OUT/'prooflab-workshop-sources.json').write_text(json.dumps(guide,indent=2)+'\n')

e=html.escape
cards=''.join(f'<details class="component"><summary><b>{e(g["id"])}</b> {e(g["name"])}</summary><p>{e(g["purpose"])}</p><ul>'+''.join(f'<li>{e(v)}</li>' for v in g['workshop_documented'])+'</ul><h3>Minor components</h3><ul>'+''.join(f'<li><b>{e(i["id"])} {e(i["name"])}</b> · {e(i["task_id"])}<br>{e(i["purpose"])}<br><small>{e(i["disposition"])}</small></li>' for i in g['items'])+'</ul></details>' for g in current_inventory)
rows=''.join(f'<tr data-owner="{e(t["owner"])}" data-priority="{e(t["priority"])}"><td>{e(t["id"])}</td><td><details><summary>{e(t["title"])}</summary><p>{e(t["technology"])}</p><p>{e(t.get("conditional_gate",""))}</p>'+''.join(f'<p><b>{e(m)}:</b> {e(", ".join(ds))}</p>' for m,ds in t.get('milestone_dependencies',{}).items())+'<ol>'+''.join(f'<li>{e(s)}</li>' for s in t['steps'])+'</ol><b>Acceptance evidence</b><ul>'+''.join(f'<li>{e(s)}</li>' for s in t['done_when'])+f'</ul><p><b>Risk:</b> {e(t["risk"])}</p></details></td><td>{e(t["owner"])}</td><td>{e(t["priority"])}</td><td>{e(", ".join(t["depends_on"]) or "—")}</td></tr>' for t in tasks)
svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1060 420" role="img" aria-labelledby="flow-title"><title id="flow-title">Supplied runtime and proposed evidence application</title><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 10 5 0 10z" fill="#53657b"/></marker></defs><style>text{font-family:system-ui,sans-serif;fill:#16202c;font-size:17px}.sub{font-size:14px;fill:#53657b}.box{fill:white;stroke:#a6b6cb;stroke-width:1.5}.ours{fill:#e9f0ff;stroke:#2563eb;stroke-width:1.5}.edge{stroke:#53657b;stroke-width:2;fill:none;marker-end:url(#arrow)}</style><rect width="1060" height="420" fill="#eef1f5"/><rect class="box" x="20" y="25" width="245" height="88" rx="12"/><text x="38" y="57">Three AgentCore agents</text><text class="sub" x="38" y="83">Supplied telecom workflow</text><rect class="box" x="310" y="25" width="260" height="88" rx="12"/><text x="328" y="57">Shared modaas-agw</text><text class="sub" x="328" y="83">Cedar + guardrails · fixed code</text><rect class="box" x="615" y="25" width="425" height="88" rx="12"/><text x="634" y="57">Approved models and governed tools</text><text class="sub" x="634" y="83">Bedrock Nemotron / AgentCore Gateway</text><path class="edge" d="M265 69H306"/><path class="edge" d="M570 69H611"/><rect class="box" x="20" y="157" width="305" height="94" rx="12"/><text x="38" y="188">Ledger · logs · CRs · metrics</text><text class="sub" x="38" y="215">Exact scope, pages and provenance</text><rect class="ours" x="375" y="157" width="315" height="94" rx="12"/><text x="393" y="188">C7 / C9 / C16 evaluators</text><text class="sub" x="393" y="215">Raw files + SQLite · IDE host</text><rect class="ours" x="740" y="157" width="300" height="94" rx="12"/><text x="758" y="188">Bounded Nemotron case</text><text class="sub" x="758" y="215">Extract → validate → cite</text><path class="edge" d="M142 113V153"/><path class="edge" d="M440 113V133H173V153"/><path class="edge" d="M325 203H371"/><path class="edge" d="M690 203H736"/><rect class="ours" x="375" y="301" width="315" height="94" rx="12"/><text x="393" y="332">Six-artifact Evidence Pack</text><text class="sub" x="393" y="359">Runnable query → official team S3</text><rect class="box" x="20" y="301" width="305" height="94" rx="12"/><text x="38" y="332">ServiceNow governance</text><text class="sub" x="38" y="359">Conditional · deterministic alerts</text><path class="edge" d="M410 251V277H173V297"/><path class="edge" d="M533 251V297"/><path class="edge" d="M890 251V348H694"/></svg>'''
(W/'workshop-flow.svg').write_text(svg)
doc='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab · Claude handoff</title><style>
:root{--bg:#eef1f5;--panel:#fff;--ink:#16202c;--muted:#53657b;--blue:#2563eb;--line:#cfdae8}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}header{background:#0b1220;color:white;padding:36px max(24px,calc((100vw - 1200px)/2))}header p{max-width:850px;color:#cbd5e1}h1{font-size:clamp(30px,4vw,48px);line-height:1.1;margin:12px 0}main{max-width:1248px;margin:auto;padding:24px;min-width:0}section{margin:24px 0}.pill{display:inline-block;background:#e5edff;color:#123f9d;padding:5px 10px;border-radius:8px;font-size:13px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.stat,.panel,.component{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;min-width:0}.stat strong{font-size:28px;display:block}.stat span,small{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.component summary{cursor:pointer;font-size:18px}.component li{margin:10px 0}summary b{color:var(--blue)}a{color:var(--blue);overflow-wrap:anywhere}header a{color:white}.button{display:inline-block;padding:10px 15px;background:var(--blue);color:white;text-decoration:none;border-radius:8px}.flow{overflow:auto}.flow svg{display:block;width:100%;min-width:650px;height:auto}input,select{font:inherit;padding:9px;border:1px solid var(--line);border-radius:8px;max-width:100%}.filters{display:flex;flex-wrap:wrap;gap:12px;margin:15px 0}.table-wrap{overflow:auto;border-radius:12px;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;min-width:720px;background:white}th,td{padding:14px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}td:nth-child(2){width:58%}th{background:#dfe7f1}td,li,p{overflow-wrap:anywhere}td summary{cursor:pointer}td li{margin:8px 0}h2{font-size:25px}h3{font-size:17px}.warn{border-left:5px solid #bd7600}.muted{color:var(--muted)}@media(max-width:700px){.stats,.grid{grid-template-columns:minmax(0,1fr)}main{padding:16px}header{padding:26px 16px}}@media(prefers-color-scheme:dark){:root{--bg:#101722;--panel:#192432;--ink:#eef3fb;--muted:#b4c1d1;--line:#38465a;--blue:#85acff}table{background:var(--panel)}th{background:#25344a}.button{background:#245dc6;color:white}input,select{background:var(--panel);color:var(--ink)}}
</style></head><body><header><span class="pill">WORKSHOP-GROUNDED · 4 OCT 2026</span><h1>A buildable context for Claude</h1><p>One portable handoff, all component responsibilities and a sequenced two-person backlog. The guide has been read; actual runtime capability and control completion still need execution evidence.</p><a class="button" href="claude-hackathon-context.txt" download>Download the full Claude context</a></header><main><div class="stats"><div class="stat"><strong>62</strong><span>Guide pages read</span></div><div class="stat"><strong>16 / 123</strong><span>Major / minor components mapped</span></div><div class="stat"><strong>50</strong><span>43 core tasks · 7 conditional bonuses</span></div><div class="stat"><strong>0 / 3</strong><span>Controls implemented in this planning work</span></div></div><section class="panel warn"><h2>Decisions that change the build</h2><ul><li>All three reference agents are documented on AgentCore; ServiceNow is a separate governance integration to verify.</li><li>C9 uses hourly runtime latency and errors. Scenario grades remain a separate diagnostic.</li><li>The shared model gateway is fixed code. Complete post-hoc C16; defer unsupported inline token prevention.</li><li>Use the actual approved Nemotron aliases; verify live approval and latency. No assumed X-Ray gateway evidence.</li><li>Official delivery is an evidence package in team S3. Confirm the deadline and AICT requirement with organizers.</li></ul></section><section class="panel"><h2>Technology in its place</h2><p class="muted">Blue blocks are proposed team software. The diagram describes the plan; it does not claim deployment. Design follows the existing ProofLab / Quest for Proof pages.</p><div class="flow">'''+svg+'''</div></section><section><h2>Complete component map</h2><p>Stable M01–M16 IDs; open a group for technologies and every minor responsibility.</p><div class="grid">'''+cards+'''</div></section><section id="tasks"><h2>Task backlog</h2><p>Start with discovery and frozen rules, then one C16 evidence slice. Begin hourly C9 collection early. All tasks remain unimplemented.</p><div class="filters"><input id="search" aria-label="Search tasks" placeholder="Search task, component or technology"><select id="priority" aria-label="Filter priority"><option value="">All priorities</option><option value="CORE">Core</option><option value="bonus">Conditional bonuses</option></select><span id="count" aria-live="polite"></span></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Task · steps · acceptance</th><th>Owner</th><th>Priority</th><th>Dependencies</th></tr></thead><tbody>'''+rows+'''</tbody></table></div></section><section class="panel"><h2>Give Claude the text file</h2><p>The primary file embeds the extracted workshop instructions, source precedence, contracts, full map, all task acceptance criteria and source directory. It does not require the old walkthrough files. JSON companions are optional for programmatic task tracking.</p><p><a href="claude-hackathon-context.txt">Full context</a> · <a href="prooflab-workshop-tasks.json">Task JSON</a> · <a href="prooflab-workshop-components.json">Component JSON</a> · <a href="prooflab-workshop-sources.json">Source index</a></p><p class="muted">Linked starter source, ServiceNow PDFs and external references were catalogued but not all inspected. Runtime tests, deployment and submission have not been performed. Credentials and bearer links are excluded.</p></section></main><script>const rows=[...document.querySelectorAll('tbody tr')];const search=document.querySelector('#search'),priority=document.querySelector('#priority');function filter(){const q=search.value.toLowerCase(),p=priority.value;let n=0;rows.forEach(r=>{const ok=r.textContent.toLowerCase().includes(q)&&(!p||(p==='CORE'?r.dataset.priority==='CORE':r.dataset.priority!=='CORE'));r.hidden=!ok;if(ok)n++});document.querySelector('#count').textContent=n+' of '+rows.length+' tasks'}search.addEventListener('input',filter);priority.addEventListener('change',filter);filter();</script></body></html>'''
lavish=ROOT/'.lavish/prooflab-workshop-handoff'
lavish.mkdir(parents=True,exist_ok=True)
(lavish/'index.html').write_text(doc)
(OUT/'prooflab-workshop-handoff.html').write_text(doc)

assert len(guide)==62 and len(current_inventory)==16 and len(assignment)==123 and len(tasks)==50
all_ids=[i['id'] for g in inventory['groups'] for i in g['items']]
assert set(all_ids)==set(assignment)
assert sum(len(t['component_ids']) for t in tasks)==123
ids={t['id'] for t in tasks}
known_guide_urls={p['url'] for p in guide}
assert len(known_guide_urls)==62
assert all(set(t['source_urls'])<=known_guide_urls for t in tasks)
assert all(set(g['source_urls'])<=known_guide_urls for g in current_inventory)
assert all(set(t['depends_on'])<=ids for t in tasks)
seen=set();active=set(); byid={t['id']:t for t in tasks}
def visit(x):
    assert x not in active, f'cycle at {x}'
    if x in seen:return
    active.add(x)
    for d in byid[x]['depends_on']:visit(d)
    active.remove(x);seen.add(x)
for x in ids:visit(x)
seen.clear();active.clear()
def milestone_visit(x):
    assert x not in active, f'milestone dependency cycle at {x}'
    if x in seen:return
    active.add(x)
    deps=set(byid[x]['depends_on'])
    for ds in byid[x].get('milestone_dependencies',{}).values():deps.update(ds)
    assert deps<=ids
    for d in deps:milestone_visit(d)
    active.remove(x);seen.add(x)
for x in ids:milestone_visit(x)
assert all(byid[d]['priority']=='CORE' for t in tasks if t['priority']=='CORE' for d in t['depends_on'])
for pat in [r'[?&](?:tkn|Signature|Policy|Key-Pair-Id|access-code)=',r'AKIA[A-Z0-9]{16}',r'ASIA[A-Z0-9]{16}',r'arn:aws:[^\s]*:\d{12}:',r'(?<!\d)\d{12}(?!\d)']:
    assert not re.search(pat,primary), f'Potential secret/identifier match {pat}'
assert not re.search(r'https?://[^\s<>]+[?&](?:tkn|Signature|Policy|Key-Pair-Id)=',doc)
report={'guide_pages':len(guide),'major_components':16,'minor_components':len(assignment),'tasks':50,'core':sum(t['priority']=='CORE' for t in tasks),'conditional_bonus':sum(t['priority']!='CORE' for t in tasks),'coverage':'all 123 minor IDs assigned once','task_dependencies':'acyclic; no CORE depends on BONUS','runtime_verified':False,'primary_bytes':len(primary.encode()),'primary_words':len(primary.split()),'primary_sha256':hashlib.sha256(primary.encode()).hexdigest(),'checks':'JSON parse, ID coverage, dependency DAG, selected credential patterns, source-link membership; no live runtime tests'}
(OUT/'prooflab-handoff-validation.json').write_text(json.dumps(report,indent=2)+'\n')
files=['claude-hackathon-context.txt','prooflab-workshop-tasks.json','prooflab-workshop-components.json','prooflab-workshop-sources.json','prooflab-workshop-handoff.html','prooflab-handoff-validation.json']
if (OUT/'prooflab-handoff-independent-reviews.txt').exists():files.append('prooflab-handoff-independent-reviews.txt')
with zipfile.ZipFile(OUT/'claude-hackathon-handoff.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in files:z.write(OUT/f,f)
print(json.dumps(report,indent=2))
