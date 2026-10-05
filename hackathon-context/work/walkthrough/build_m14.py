from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M14_START -->.*?<!-- M14_END -->','',s,flags=re.S)
body=(site/'m14-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M13','ProofLab walkthrough · M01–M14')
s=s.replace('This page currently covers M01–M13; each has its own walkthrough.','This page currently covers M01–M14; each has its own walkthrough.')
if 'href="#M14"' not in s:s=s.replace('<nav>','<nav><a href="#M14">M14 governance</a>',1)
s=s.replace('NEXT · M14','CONTINUE BELOW · M14')
s=s.replace('<footer>','<!-- M14_START -->'+body+'<!-- M14_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M14 ServiceNow governance and human oversight</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M14</strong><nav><a href="#m14-boundary">Records</a><a href="#m14-intent">Finding</a><a href="#m14-uncertain">Uncertainty</a><a href="#m14-human">Owner</a><a href="#m14-close">Closure</a><a href="#m14-parts">Six parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass slides and meeting transcript; current control foundation, reviewed M08/M11–M13 contracts and component inventory. Integration routes, state names, delivery protocol and example story are proposed design choices, not implemented ServiceNow functionality.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; exported HTML checked. No browser-rendering verification or live connection, delivery, notification, response, remediation or retest performed.</p></footer></main></body></html>'''
(site/'m14.html').write_text(standalone)
shutil.copy2(site/'m14-governance.svg',out/'prooflab-m14-governance.svg')
print('Updated cumulative M01–M14 walkthrough and focused M14 chapter.')
