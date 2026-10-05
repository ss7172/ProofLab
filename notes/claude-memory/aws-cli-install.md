---
name: aws-cli-install
description: "AWS CLI on this Mac is the official pkg in ~/aws-cli, not Homebrew — Homebrew python@3.14 has a broken pyexpat"
metadata:
  node_type: memory
  type: reference
  originSessionId: ca14fa49-a079-47de-a9fb-a38b37dcff99
  modified: 2026-10-04T18:26:48.539Z
---

`aws` is the official AWS CLI v2 installed per-user at ~/aws-cli, symlinked into /opt/homebrew/bin/aws. Homebrew's awscli was removed because Homebrew python@3.14 (3.14.8) fails with `Symbol not found: _XML_SetAllocTrackerActivationThreshold` (pyexpat built against newer libexpat than macOS 26.2 ships). Any Homebrew-Python tool that imports pyexpat will hit the same error until macOS or the bottle is updated.

Related: [[workshop-aws-access]]
