from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M10_START -->.*?<!-- M10_END -->','',s,flags=re.S)
body=(site/'m10-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M09','ProofLab walkthrough · M01–M10')
s=s.replace('This page currently covers M01–M09; each has its own walkthrough.','This page currently covers M01–M10; each has its own walkthrough.')
if 'href="#M10"' not in s:s=s.replace('<nav>','<nav><a href="#M10">M10 admission</a>',1)
s=s.replace('NEXT · M10','CONTINUE BELOW · M10')
s=s.replace('<footer>','<!-- M10_START -->'+body+'<!-- M10_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M10 Optional inline admission coordinator</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M10</strong><nav><a href="#m10-placement">Placement</a><a href="#m10-reserve">Concurrent calls</a><a href="#m10-states">States</a><a href="#m10-finality">Settlement</a><a href="#m10-close">Closure</a><a href="#m10-parts">Eight parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass Control 16 shared-model-gateway example and accounting/prevention scope; current reviewed architecture foundation and V4 model scope. The atomic protocol, conservative bound retention and request contracts are proposed design choices. Values are illustrative, not actual endpoint measurements.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; exported HTML and illustrative arithmetic checked. No browser-rendering verification or live concurrency, crash, storage, gateway or provider integration test performed.</p></footer></main></body></html>'''
(site/'m10.html').write_text(standalone)
shutil.copy2(site/'m10-admission.svg',out/'prooflab-m10-admission.svg')
print('Updated cumulative M01–M10 walkthrough and focused M10 chapter.')
