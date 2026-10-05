from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M15_START -->.*?<!-- M15_END -->','',s,flags=re.S)
body=(site/'m15-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M14','ProofLab walkthrough · M01–M15')
s=s.replace('This page currently covers M01–M14; each has its own walkthrough.','This page currently covers M01–M15; each has its own walkthrough.')
if 'href="#M15"' not in s:s=s.replace('<nav>','<nav><a href="#M15">M15 validation</a>',1)
s=s.replace('NEXT · M15','CONTINUE BELOW · M15')
s=s.replace('<footer>','<!-- M15_START -->'+body+'<!-- M15_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M15 Validation and submission packaging</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M15</strong><nav><a href="#m15-states">Results</a><a href="#m15-adversarial">Tests</a><a href="#m15-model">Model quality</a><a href="#m15-six">Six artifacts</a><a href="#m15-release">Readiness</a><a href="#m15-parts">Eight parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied masterclass task/judging/deliverable slides, meeting transcript and current architecture contracts. Test manifests, release states, offline checker and model-quality/latency gates are proposed design choices. This document is not the submission bundle or runnable control tool.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; exported HTML checked. No browser-rendering verification or control campaign, live integration, model benchmark, offline recheck or timed judge rehearsal performed.</p></footer></main></body></html>'''
(site/'m15.html').write_text(standalone)
shutil.copy2(site/'m15-validation.svg',out/'prooflab-m15-validation.svg')
print('Updated cumulative M01–M15 walkthrough and focused M15 chapter.')
