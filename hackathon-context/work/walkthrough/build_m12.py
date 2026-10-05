from pathlib import Path
import shutil,re

root=Path.cwd();site=root/'.lavish/prooflab-walkthrough';out=root/'outputs'
p=site/'index.html';s=p.read_text()
s=re.sub(r'<!-- M12_START -->.*?<!-- M12_END -->','',s,flags=re.S)
body=(site/'m12-body.html').read_text()
s=s.replace('ProofLab walkthrough · M01–M11','ProofLab walkthrough · M01–M12')
s=s.replace('This page currently covers M01–M11; each has its own walkthrough.','This page currently covers M01–M12; each has its own walkthrough.')
if 'href="#M12"' not in s:s=s.replace('<nav>','<nav><a href="#M12">M12 validation</a>',1)
s=s.replace('NEXT · M12','CONTINUE BELOW · M12')
s=s.replace('<footer>','<!-- M12_START -->'+body+'<!-- M12_END --><footer>',1)
p.write_text(s)
css=s.split('<style>',1)[1].split('</style>',1)[0]
standalone='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M12 Evidence validation and assessment composition</title><style>'''+css+'''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M12</strong><nav><a href="#m12-proposal">Proposal</a><a href="#m12-checks">Checks</a><a href="#m12-verified">Verified as what?</a><a href="#m12-revisions">Revisions</a><a href="#m12-claim">Claim</a><a href="#m12-parts">Eight parts</a></nav></header><main class="wrap">'''+body+'''<footer><p>Sources: supplied hackathon claim/control structure, dated-threshold and evidence requirements; current control foundation and V4 NVIDIA promotion/case contracts. Validators, typed records, concurrency protocol and invented note/revision examples are proposed implementation choices.</p><p>Design source: existing Quest for Proof page tokens and layout, retained for continuity. SVG rendered and visually inspected; exported HTML and illustrative composition table checked. No browser-rendering verification or live validator, source, revision-concurrency or publication integration test performed.</p></footer></main></body></html>'''
(site/'m12.html').write_text(standalone)
shutil.copy2(site/'m12-validation.svg',out/'prooflab-m12-validation.svg')
print('Updated cumulative M01–M12 walkthrough and focused M12 chapter.')
