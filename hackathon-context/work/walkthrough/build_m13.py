from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M13_START -->.*?<!-- M13_END -->','',s,flags=re.S)
body=(site/'m13-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M12','ProofLab walkthrough · M01–M13')
s=s.replace('This page currently covers M01–M12; each has its own walkthrough.','This page currently covers M01–M13; each has its own walkthrough.')
if 'href="#M13"' not in s:s=s.replace('<nav>','<nav><a href="#M13">M13 query</a>',1)
s=s.replace('NEXT · M13','CONTINUE BELOW · M13')
s=s.replace('<footer>','<!-- M13_START -->'+body+'<!-- M13_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M13 Judge query and case assembly</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M13</strong><nav><a href="#m13-select">Scope</a><a href="#m13-profiles">Profiles</a><a href="#m13-screen">First view</a><a href="#m13-retries">Recovery</a><a href="#m13-offline">Offline</a><a href="#m13-parts">Eight parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass query/two-minute and six-artifact requirements; current control foundation, V4 NVIDIA bounded workflow and reviewed M11/M12 contracts. Query profiles, recovery protocol and illustrative screen are proposed design choices, not an implemented application.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; exported HTML checked. No browser-rendering verification or live query, model, replay, cancellation, publication or latency test performed.</p></footer></main></body></html>'''
(site/'m13.html').write_text(standalone)
shutil.copy2(site/'m13-query.svg',out/'prooflab-m13-query.svg')
print('Updated cumulative M01–M13 walkthrough and focused M13 chapter.')
