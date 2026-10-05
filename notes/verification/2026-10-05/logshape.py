# Summarise log lines from stdin WITHOUT printing secrets: key inventory, categorical values, redacted non-JSON samples.
import sys, json, re, collections
SENS = re.compile(r'key|token|secret|auth|cookie|pass|signature|bearer|credential|jwt', re.I)
RUN = re.compile(r'[A-Za-z0-9+/=_\-\.]{16,}')
def red(s):
    s = re.sub(r'(?i)(bearer|basic)\s+\S+', r'\1 <R>', s)
    s = re.sub(r'(?i)((?:api[_-]?key|token|authorization|secret|password)["\']?\s*[:=]\s*["\']?)[^\s"\',}]+', r'\1<R>', s)
    return RUN.sub(lambda m: '<R>' if (re.search(r'\d', m.group()) and re.search(r'[A-Za-z]', m.group())) else m.group(), s)
lines = [l for l in sys.stdin.read().splitlines() if l.strip()]
keys = collections.Counter(); vals = collections.defaultdict(collections.Counter); nonjson = []
def walk(o, p=''):
    for k, v in o.items():
        kp = p + k; keys[kp] += 1
        if isinstance(v, dict): walk(v, kp + '.')
        elif not SENS.search(kp) and not isinstance(v, list): vals[kp][red(str(v))[:70]] += 1
for l in lines:
    i = l.find('{'); obj = None
    if i >= 0:
        try: obj = json.loads(l[i:])
        except Exception: obj = None
    if isinstance(obj, dict): walk(obj)
    else: nonjson.append(l)
print('lines', len(lines), 'json', len(lines) - len(nonjson), 'nonjson', len(nonjson))
for k, c in keys.most_common(70):
    v = vals.get(k)
    if SENS.search(k): desc = '[sensitive-name: values suppressed]'
    elif v is None: desc = ''
    elif len(v) <= 8: desc = ' | '.join(f'{x} x{n}' for x, n in v.most_common(8))
    else: desc = f'{len(v)} distinct, e.g. ' + ' | '.join(x for x, _ in v.most_common(2))
    print(f'  {k} ({c}): {desc}'[:400])
shapes = collections.OrderedDict()
for l in nonjson:
    s = red(l); shp = re.sub(r'\d', '9', s)[:60]
    if shp not in shapes: shapes[shp] = (s[:300], 0)
    shapes[shp] = (shapes[shp][0], shapes[shp][1] + 1)
for shp, (s, n) in list(shapes.items())[:15]: print(f'  NONJSON x{n}: {s}')
