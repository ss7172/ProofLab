from pathlib import Path
import shutil,re
root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
if '<!-- M02_START -->' in s:s=s[:s.index('<!-- M02_START -->')]+s[s.index('<!-- M02_END -->')+len('<!-- M02_END -->'):]
body=(site/'m02-body.html').read_text()
s=s.replace('This chapter covers M01 only.','This page currently covers M01 and M02; each has its own walkthrough.')
s=s.replace('<title>ProofLab walkthrough · M01 telecom workflow</title>','<title>ProofLab walkthrough · M01 and M02</title>')
if 'href="#M02"' not in s:s=s.replace('<nav>','<nav><a href="#M02">M02 adapters</a>',1)
s=s.replace('NEXT · M02','CONTINUE BELOW · M02')
s=s.replace('<footer>','<!-- M02_START -->'+body+'<!-- M02_END --><footer>',1)
s=s.replace('physical slide 17, visually inspected; corresponding supplied meeting-transcript passage;','physical slide 17, visually inspected, and slides 12–15 for M02 contracts; corresponding supplied meeting-transcript passage;')
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M02 enforcement points and adapters</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M02</strong><nav><a href="#m02-story">Request walkthrough</a><a href="#m02-routing">Control mapping</a><a href="#m02-transports">Four interfaces</a><a href="#m02-parts">Eight parts</a></nav></header><main class="wrap">'''+body+'''<footer>Source: supplied masterclass slides12–15 and current reviewed V4 architecture/control foundation. Proposed interfaces and synthetic numbers; no live integration claimed. Existing Quest for Proof design tokens reused. SVG rendered and visually inspected; HTML checked statically, not browser-rendered.</footer></main></body></html>'''
(site/'m02.html').write_text(standalone)
shutil.copy2(site/'m02-flow.svg',out/'prooflab-m02-flow.svg')
# Make callback's delayed-verdict purpose explicit in the shared inventory source.
p=root/'work/component-inventory/build_inventory.py';t=p.read_text().replace("i('Later-result callback contract','Correlates delayed results through a supported source integration; a generic callback demo is optional.')","i('Later-verdict/result callback contract','Correlates authenticated, duplicate-safe delayed verdicts/results such as deferred human decisions; a generic callback demonstration is optional.')")
p.write_text(t)
print('Added M02 to cumulative walkthrough and wrote focused chapter.')
