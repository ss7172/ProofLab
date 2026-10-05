from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M09_START -->.*?<!-- M09_END -->','',s,flags=re.S)
body=(site/'m09-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M08','ProofLab walkthrough · M01–M09')
s=s.replace('This page currently covers M01–M08; each has its own walkthrough.','This page currently covers M01–M09; each has its own walkthrough.')
if 'href="#M09"' not in s:s=s.replace('<nav>','<nav><a href="#M09">M09 accounting</a>',1)
s=s.replace('NEXT · M09','CONTINUE BELOW · M09')
s=s.replace('<footer>','<!-- M09_START -->'+body+'<!-- M09_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M09 Control 16 token accounting</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M09</strong><nav><a href="#m09-scope">Scope</a><a href="#m09-units">What counts?</a><a href="#m09-example">Worked example</a><a href="#m09-verdicts">Verdicts</a><a href="#m09-contract">Interface</a><a href="#m09-parts">Five parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass's Control 16 objective and shared-gateway worked example (printed slide 21: FM-A 9,600 / FM-B 10,800 / cap 10,000 / zero over-cap runs), frozen-threshold and judging requirements; current reviewed architecture foundation and V4 Nemotron amendment. The detailed execution, evidence and module contracts are our proposed implementation.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; HTML and illustrative arithmetic checked. No browser-rendering verification or live accounting/prevention integration test performed.</p></footer></main></body></html>'''
(site/'m09.html').write_text(standalone)
shutil.copy2(site/'m09-accounting.svg',out/'prooflab-m09-accounting.svg')
print('Updated cumulative M01–M09 walkthrough and focused M09 chapter.')
