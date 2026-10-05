from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M08_START -->.*?<!-- M08_END -->','',s,flags=re.S)
body=(site/'m08-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M07','ProofLab walkthrough · M01–M08')
s=s.replace('This page currently covers M01–M07; each has its own walkthrough.','This page currently covers M01–M08; each has its own walkthrough.')
if 'href="#M08"' not in s:s=s.replace('<nav>','<nav><a href="#M08">M08 drift</a>',1)
s=s.replace('NEXT · M08','CONTINUE BELOW · M08')
s=s.replace('<footer>','<!-- M08_START -->'+body+'<!-- M08_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M08 Control 9 performance drift</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M08</strong><nav><a href="#m08-metric">What is scored?</a><a href="#m08-baseline">Baseline</a><a href="#m08-calculation">Worked example</a><a href="#m08-missing">Missing results</a><a href="#m08-alerts">Alerts</a><a href="#m08-parts">Eight parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass's Control 9 objective, worked C7/C9 slide (baseline 0.900, W10 0.792, 12% relative drop), frozen-threshold and human-response scope requirements; current reviewed architecture foundation and V4 Nemotron amendment. Exact-match scoring, campaign design and module contracts are our proposed implementation.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; HTML and illustrative arithmetic checked. No browser-rendering verification or live performance/alert integration test performed.</p></footer></main></body></html>'''
(site/'m08.html').write_text(standalone)
shutil.copy2(site/'m08-drift.svg',out/'prooflab-m08-drift.svg')
print('Updated cumulative M01–M08 walkthrough and focused M08 chapter.')
