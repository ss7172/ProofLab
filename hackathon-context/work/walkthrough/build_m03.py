from pathlib import Path
import shutil, re

root = Path.cwd()
site = root / '.lavish/prooflab-walkthrough'
out = root / 'outputs'
p = site / 'index.html'
s = p.read_text()
s = re.sub(r'<!-- M03_START -->.*?<!-- M03_END -->', '', s, flags=re.S)
body = (site / 'm03-body.html').read_text()
s = s.replace('ProofLab walkthrough · M01 and M02', 'ProofLab walkthrough · M01–M03')
s = s.replace('This page currently covers M01 and M02; each has its own walkthrough.', 'This page currently covers M01–M03; each has its own walkthrough.')
if 'href="#M03"' not in s:
    s = s.replace('<nav>', '<nav><a href="#M03">M03 identity</a>', 1)
s = s.replace('NEXT · M03', 'CONTINUE BELOW · M03')
s = s.replace('<footer>', '<!-- M03_START -->' + body + '<!-- M03_END --><footer>', 1)
s = s.replace('and slides 12–15 for M02 contracts;', 'slides 12–15 for invocation/binding contracts, and the worked Control 16 example for run/call identity;')
p.write_text(s)
css = s.split('<style>', 1)[1].split('</style>', 1)[0]
standalone = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ProofLab walkthrough · M03 identity, schemas and lifecycle</title><style>''' + css + '''</style></head><body><header class="top"><strong>QUEST FOR PROOF / M03</strong><nav><a href="#m03-identities">Six identities</a><a href="#m03-story">Follow the run</a><a href="#m03-edge-cases">Retries</a><a href="#m03-lifecycle">Lifecycle</a><a href="#m03-parts">Six parts</a><a href="#m03-review">Independent review</a></nav></header><main class="wrap">''' + body + '''<footer><p>Sources: supplied masterclass's invocation/evidence-binding slides and worked Control 16 example; reviewed architecture foundation and V4 Nemotron amendment. Fine-grained identities and lifecycle rules are our proposed design, not organizer-mandated field names.</p><p>Design source: existing Quest for Proof page tokens and layout. SVG rendered and visually inspected; HTML checked statically. No browser-rendering verification or live integration performed.</p></footer></main></body></html>'''
(site / 'm03.html').write_text(standalone)
shutil.copy2(site / 'm03-identity.svg', out / 'prooflab-m03-identity.svg')
print('Updated cumulative M01–M03 page and focused M03 chapter.')
