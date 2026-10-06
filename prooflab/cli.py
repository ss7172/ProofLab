"""The single `python3 -m prooflab <verb>` dispatcher (G-19). Stdlib, Python 3.9.

Verbs map by name to "module:function" and are imported lazily, so one broken or unbuilt verb never
breaks the others. A later PR adds a verb by adding ONE line to VERBS (via the contract owner, PR-01).
The target function takes argv (list of str, the args after the verb) and returns an int exit code.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys

# verb -> (target "module:function", one-line help, owning PR). Every target lives under prooflab.* (FEATURE-MAP R1).
VERBS = {
    "run": ("prooflab.adapters.orchestrator.run:main", "drive one run of the ifabric- trio (EP-5; EP-0 preflight)",
            "PR-08a"),
    "registry": ("prooflab.registry.cli:main", "registry tooling: freeze, pin, check (needs cli.py in PR-11's owns)",
                 "PR-11"),
    "query": ("prooflab.query.cli:main", "the control test: query a control for a run or window", "PR-15a"),
    "assess": ("prooflab.query.cli:assess_main", "run the control tests and write assessments", "PR-15a"),
    "refresh": ("prooflab.store.snapshot:main", "snapshot the one store (with the check poller)", "PR-13a"),
    "pack": ("prooflab.pack.build:main", "build / index / verify the Evidence Pack", "PR-21"),
    "humanloop": ("prooflab.humanloop.runner:main", "the human loop: findings -> ServiceNow, mirror", "PR-20a"),
    "console": ("prooflab.console.server:main", "the Evidence Console (loopback; PACK and LIVE)", "PR-17"),
    "watch": ("prooflab.watch.cli:main", "live feed + the response poller (check --cutoff)", "PR-14"),
    "tail": ("prooflab.watch.tail:main", "tail the live index", "PR-14"),
    "recheck": ("prooflab.recheck.cli:main", "independent arithmetic recheck of assessments", "PR-10"),
    "collect": ("prooflab.adapters.collectors.cli:main",
                "pull platform evidence by run id and window (needs cli.py in PR-12a's owns)", "PR-12a"),
    "postrun": ("prooflab.adapters.postrun.cli:main", "EP-2 post-run replay of the C16 decisions", "PR-23"),
    "servicenow": ("prooflab.servicenow.cli:main", "Arth's ServiceNow adapter CLI (handoff-3, unchanged)", "Arth"),
}
# Aliases: an old spelling -> its verb.
ALIASES = {"register": "registry"}

EXIT_USAGE = 2
EXIT_NOT_BUILT = 3


def _split(target: str):
    module, _, func = target.partition(":")
    return module, func or "main"


def is_built(verb: str) -> bool:
    module, _ = _split(VERBS[verb][0])
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def usage() -> str:
    lines = ["usage: python3 -m prooflab <verb> [args...]", "", "verbs:"]
    for verb in sorted(VERBS):
        target, text, owner = VERBS[verb]
        status = "" if is_built(verb) else "  [not built yet: %s]" % owner
        lines.append("  %-11s %s%s" % (verb, text, status))
    lines.append("")
    lines.append("python3 -m prooflab <verb> --help  for a verb's own options")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
        return 0 if argv else EXIT_USAGE
    verb, rest = argv[0], argv[1:]
    verb = ALIASES.get(verb, verb)
    if verb not in VERBS:
        print("prooflab: unknown verb %r\n\n%s" % (verb, usage()), file=sys.stderr)
        return EXIT_USAGE
    module_name, func_name = _split(VERBS[verb][0])
    if not is_built(verb):
        print("prooflab %s: not built yet (module %s, owner %s)" % (verb, module_name, VERBS[verb][2]),
              file=sys.stderr)
        return EXIT_NOT_BUILT
    module = importlib.import_module(module_name)
    func = getattr(module, func_name, None)
    if func is None:
        print("prooflab %s: %s has no %s()" % (verb, module_name, func_name), file=sys.stderr)
        return EXIT_NOT_BUILT
    result = func(rest)
    return int(result or 0)
