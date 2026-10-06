from pathlib import Path
_T = Path(__file__).parent
exec(compile((_T / "agent_C_all_modules_loader.py").read_text(encoding="utf-8"), "agent_C_all_modules_loader.py", "exec"), {"__name__": "bundle"})
import prooflab, prooflab.servicenow.assurance_agent as _aa
prooflab.__path__.append(str(_T / "prooflab"))          # so prooflab.tests (on disk) is importable next to the bundled modules
assert type(_aa.__loader__).__name__ == "_BundleFinder", _aa.__loader__
