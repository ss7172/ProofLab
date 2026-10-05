from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M11_START -->.*?<!-- M11_END -->','',s,flags=re.S)
body=(site/'m11-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M10','ProofLab walkthrough · M01–M11')
s=s.replace('This page currently covers M01–M10; each has its own walkthrough.','This page currently covers M01–M11; each has its own walkthrough.')
if 'href="#M11"' not in s:s=s.replace('<nav>','<nav><a href="#M11">M11 Nemotron</a>',1)
s=s.replace('NEXT · M11','CONTINUE BELOW · M11')
s=s.replace('<footer>','<!-- M11_START -->'+body+'<!-- M11_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M11 Nemotron Evidence Investigator</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M11</strong><nav><a href="#m11-example">Example</a><a href="#m11-authority">Authority</a><a href="#m11-flow">Two calls</a><a href="#m11-budget">One minute?</a><a href="#m11-own-usage">Own usage</a><a href="#m11-parts">Eleven parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass and meeting transcript for Nemotron use, model slide, provided runtime and judging scope; current V4 NVIDIA architecture and reviewed control foundation. Public NVIDIA NIM function-calling and structured-generation references are linked above; they do not establish workshop access. Timings, model profiles and this investigator are proposed design choices.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; exported HTML and proposed stage-budget arithmetic checked. No browser-rendering verification, model call, extraction evaluation or latency benchmark performed.</p></footer></main></body></html>'''
(site/'m11.html').write_text(standalone)
shutil.copy2(site/'m11-investigator.svg',out/'prooflab-m11-investigator.svg')
print('Updated cumulative M01–M11 walkthrough and focused M11 chapter.')
