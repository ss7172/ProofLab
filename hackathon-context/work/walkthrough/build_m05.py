from pathlib import Path
import shutil, re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M05_START -->.*?<!-- M05_END -->','',s,flags=re.S)
body=(site/'m05-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M04','ProofLab walkthrough · M01–M05')
s=s.replace('This page currently covers M01–M04; each has its own walkthrough.','This page currently covers M01–M05; each has its own walkthrough.')
if 'href="#M05"' not in s:s=s.replace('<nav>','<nav><a href="#M05">M05 acquisition</a>',1)
s=s.replace('NEXT · M05','CONTINUE BELOW · M05')
s=s.replace('<footer>','<!-- M05_START -->'+body+'<!-- M05_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M05 evidence acquisition and reconciliation</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M05</strong><nav><a href="#m05-sources">Two inputs</a><a href="#m05-story">Follow the records</a><a href="#m05-completeness">Completeness</a><a href="#m05-authority">Conflicts</a><a href="#m05-parts">Nine parts</a><a href="#m05-review">Review</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass deck's lab/collector description, evidence-binding pattern, whole-run Control 16 example and coverage/judging requirements; current reviewed architecture foundation and V4 Nemotron amendment. Independent expected-work contracts, source recovery rules and module boundaries are our proposed engineering design.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; HTML checked statically. No browser-rendering verification or live source integration performed.</p></footer></main></body></html>'''
(site/'m05.html').write_text(standalone)
shutil.copy2(site/'m05-acquisition.svg',out/'prooflab-m05-acquisition.svg')
print('Updated cumulative M01–M05 walkthrough and focused M05 chapter.')
