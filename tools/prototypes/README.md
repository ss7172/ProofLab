# tools/prototypes: rescued prototypes (not product code)

Rescued from the planning session's scratchpad (`architecture/work/13-prototypes/`, T0.7) so they survive cleanup.
They use fakes and stubs only. Not imported by the product; to be productised by T3.3 (bundler) and T6.1 (Assurance handler).

- `assurance/`: the one-file Assurance bundle prototype. `make_bundle.py` writes `agent_A_analyzer_only.py`
  (Arth's unchanged `nemotron.py` behind an importlib finder plus `shim_analyzer.py`); `e2e_glue.py` runs it
  end to end against `stub/bedrock_agentcore`. `agent_B_orchestrator.py` and `agent_C_all_modules.py` are larger variants.
- `assurance/bundletest/`: `conftest.py`, `pytest.ini` and `agent_C_all_modules_loader.py` (Arth's 152 tests served
  from one generated file). The byte-identical copy of Arth's `prooflab/` that it expects is NOT copied here; the
  repo's own `prooflab/` serves that role.
- `servicenow/repro_bugs.py`: reproduces the two confirmed adapter bugs (accepted risks (a) and (b), ARCH §3.8).
