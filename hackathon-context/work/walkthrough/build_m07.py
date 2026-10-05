from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M07_START -->.*?<!-- M07_END -->','',s,flags=re.S)
body=(site/'m07-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M06','ProofLab walkthrough · M01–M07')
s=s.replace('This page currently covers M01–M06; each has its own walkthrough.','This page currently covers M01–M07; each has its own walkthrough.')
if 'href="#M07"' not in s:s=s.replace('<nav>','<nav><a href="#M07">M07 event tests</a>',1)
s=s.replace('NEXT · M07','CONTINUE BELOW · M07')
s=s.replace('<footer>','<!-- M07_START -->'+body+'<!-- M07_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M07 Control 7 event recording</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M07</strong><nav><a href="#m07-coverage">Coverage</a><a href="#m07-timing">Timing</a><a href="#m07-missing">Missing event</a><a href="#m07-cutoffs">Deadlines</a><a href="#m07-parts">Five parts</a><a href="#m07-review">Review</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass's governance objective tree, worked C7/C9 examples (11 events; gaps 2,3,4,2,8,3,2,4,3,2 ms), threshold and task requirements; current reviewed architecture foundation. Pair inventories, clock checks and missing-evidence semantics are our proposed implementation design.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; HTML and illustrative arithmetic checked. No browser-rendering verification or live control implementation tested.</p></footer></main></body></html>'''
(site/'m07.html').write_text(standalone)
shutil.copy2(site/'m07-tests.svg',out/'prooflab-m07-tests.svg')
print('Updated cumulative M01–M07 walkthrough and focused M07 chapter.')
