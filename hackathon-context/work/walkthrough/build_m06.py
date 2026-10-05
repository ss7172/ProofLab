from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M06_START -->.*?<!-- M06_END -->','',s,flags=re.S)
body=(site/'m06-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M05','ProofLab walkthrough · M01–M06')
s=s.replace('This page currently covers M01–M05; each has its own walkthrough.','This page currently covers M01–M06; each has its own walkthrough.')
if 'href="#M06"' not in s:s=s.replace('<nav>','<nav><a href="#M06">M06 workspace</a>',1)
s=s.replace('NEXT · M06','CONTINUE BELOW · M06')
s=s.replace('<footer>','<!-- M06_START -->'+body+'<!-- M06_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M06 shared evidence workspace</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M06</strong><nav><a href="#m06-layers">What is stored?</a><a href="#m06-story">Follow P-091</a><a href="#m06-binding">Control bindings</a><a href="#m06-snapshots">Frozen revisions</a><a href="#m06-parts">Seven parts</a><a href="#m06-review">Review</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass's evidence binding, ledger/control-test separation and portable submission requirements; current reviewed architecture foundation and V4 Nemotron amendment. Typed repositories, exact revision keys, candidate promotion and publication behavior are our proposed engineering design.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; HTML checked statically. No browser-rendering verification or live storage/integration test performed.</p></footer></main></body></html>'''
(site/'m06.html').write_text(standalone)
shutil.copy2(site/'m06-workspace.svg',out/'prooflab-m06-workspace.svg')
print('Updated cumulative M01–M06 walkthrough and focused M06 chapter.')
