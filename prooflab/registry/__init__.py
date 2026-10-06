"""The control registry (ARCH §3.3). parse.py is the contract owner's (PR-01); freeze/pin tooling is PR-11's.

`python3 -m prooflab registry <sub> [args]` lands in main() below, a lazy sub-dispatcher over PR-11's
per-module entry points (each exposes main(argv) -> int). Nothing is imported until a sub-verb is run,
so `import prooflab.registry.parse` stays free of PR-11's modules.
"""

# sub-verb -> (module, one-line help). Module paths are the ones PR-11 ships (pr/PR-11-registry e0a9d37).
SUBVERBS = {
    "freeze": ("prooflab.registry.freeze", "freeze register + risks as one version (ARCH 3.3, 3.9)"),
    "pin": ("prooflab.registry.pinned", "in-path pins from a frozen register (ARCH 3.3 steps 5-6)"),
    "derive": ("prooflab.registry.derive", "threshold derivation from the pilots (ARCH 5.4 step 5)"),
    "inventory": ("prooflab.registry.inventory", "freeze the AI inventory (inv-N) + cross-checks (ARCH 3.10)"),
    "approval-finding": ("prooflab.registry.approval_finding", "the T2 approval Finding from the frozen bytes (G-13)"),
    "run-ids": ("prooflab.registry.named_runs", "check run-ids.txt (ARCH 5.4 rule 8)"),
}

EXIT_USAGE = 2
EXIT_NOT_BUILT = 3


def usage() -> str:
    lines = ["usage: python3 -m prooflab registry <sub> [args...]", "", "subcommands:"]
    for sub in sorted(SUBVERBS):
        lines.append("  %-17s %s" % (sub, SUBVERBS[sub][1]))
    return "\n".join(lines)


def main(argv=None) -> int:
    import importlib
    import importlib.util
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage())
        return 0 if argv else EXIT_USAGE
    sub, rest = argv[0], argv[1:]
    if sub not in SUBVERBS:
        print("prooflab registry: unknown subcommand %r\n\n%s" % (sub, usage()), file=sys.stderr)
        return EXIT_USAGE
    module_name = SUBVERBS[sub][0]
    try:
        found = importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        found = False
    if not found:
        print("prooflab registry %s: not built yet (module %s, owner PR-11)" % (sub, module_name), file=sys.stderr)
        return EXIT_NOT_BUILT
    func = getattr(importlib.import_module(module_name), "main", None)
    if func is None:
        print("prooflab registry %s: %s has no main()" % (sub, module_name), file=sys.stderr)
        return EXIT_NOT_BUILT
    return int(func(rest) or 0)
