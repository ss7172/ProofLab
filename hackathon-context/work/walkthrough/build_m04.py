from pathlib import Path
import shutil, re

root=Path.cwd(); site=root/'.lavish/prooflab-walkthrough'; out=root/'outputs'
p=site/'index.html'; s=p.read_text()
s=re.sub(r'<!-- M04_START -->.*?<!-- M04_END -->','',s,flags=re.S)
body=(site/'m04-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M03','ProofLab walkthrough · M01–M04')
s=s.replace('This page currently covers M01–M03; each has its own walkthrough.','This page currently covers M01–M04; each has its own walkthrough.')
if 'href="#M04"' not in s:s=s.replace('<nav>','<nav><a href="#M04">M04 policy</a>',1)
s=s.replace('NEXT · M04','CONTINUE BELOW · M04')
s=s.replace('<footer>','<!-- M04_START -->'+body+'<!-- M04_END --><footer>',1)
s=s.replace('current V4 component inventory.', 'current V4 component inventory. M04 also references the deck’s threshold, register and judging requirements.')
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M04 policy register and applicability</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M04</strong><nav><a href="#m04-rule">What is a rule?</a><a href="#m04-story">Follow FM-001</a><a href="#m04-mapping">Control mapping</a><a href="#m04-changes">Policy changes</a><a href="#m04-parts">Six parts</a><a href="#m04-review">Review</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass deck, physical pages 10 (thresholds), 14–15 (architecture/register), 20–21 (objectives/worked example), 25–26 (judging/deliverables); current reviewed architecture foundation and V4 Nemotron amendment. Module names, fine-grained version keys and expiry/revocation behavior are our proposed design.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; HTML checked statically. No browser-rendering verification or live integration performed.</p></footer></main></body></html>'''
(site/'m04.html').write_text(standalone)
shutil.copy2(site/'m04-policy.svg',out/'prooflab-m04-policy.svg')
print('Updated cumulative M01–M04 walkthrough and focused M04 chapter.')
