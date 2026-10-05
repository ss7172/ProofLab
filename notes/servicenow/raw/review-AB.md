# Review of notes A and B against the two ServiceNow PDFs

An independent, read-only reviewer prepared this on 2026-10-05. No existing file was edited. There were no AWS calls and no git.

**Method**
- Read the text layer of each PDF page by page with `pdftotext -layout`.
- Read the metadata with `pdfinfo`.
- Extracted the embedded screenshots with `pdfimages` (A: 2400×1203; B: 1920×963) and viewed them at native or near-native size.
- Cropped one region (A p10) with `sips`.
- The temp image folder `review-tmp/` was deleted afterwards.

**Template:** `workshop-static/servicenow/03-servicenow-aict.yaml` (441 lines).

**Verdict labels**
- **CONFIRMED**: the PDF or template says or shows it.
- **WRONG**: contradicted by the PDF or template.
- **OVERSTATED**: goes beyond the evidence, or is inference cited as PDF.
- **n/c**: not re-checked in this pass.

Claims tagged LIVE, KNOWN, M11 or Team-notes were not re-verified. They are out of scope, and checking them would need AWS access.

## Verdicts

- **Note A (connection setup): sound.**
  - Every claim the caller flagged is CONFIRMED: the required fields, the bare role name, the schedules, and all six template line references.
  - Four items are OVERSTATED: D2's PDF clause, D4's "will not submit", the Bedrock-Model nesting, and D12's wording.
  - One literal statement is WRONG: "the words 'invocation'… do not appear" in the PDF.
- **Note B (AICT console): sound.**
  - Every claim the caller flagged is CONFIRMED.
  - Four items are OVERSTATED: §0.5's "no AWS agent among evaluated sessions", the §7 connector-name "discrepancy", "Managed by = the presenter", and the §0.7 Secrets Detection framing.
  - Nothing found is WRONG.

---

## Note A: `A-connection-setup.md` vs `creating-and-verifying-amazon-connection-setup.pdf`

### A1. File facts

| Claim | Verdict | Evidence |
|---|---|---|
| 12 A4 pages, react-pdf, 2026-09-30 12:15 CDT | CONFIRMED | pdfinfo: Pages 12, A4, CreationDate Wed Sep 30 12:15:29 2026 CDT |
| md5 d1c21c83…, byte-identical to the kit copy | CONFIRMED | Both files hash to `d1c21c838ffa36fb8d2ead9a6e9449c1` |
| One 2400×1203 screenshot per step | CONFIRMED | p2–p11 are 2400×1203. p1 is a 1920×1080 thumbnail. p12 has no screenshot. |

### A2. The flagged form-field claims (p4–p8)

| Claim | Verdict | Evidence |
|---|---|---|
| Intro text "Select the AWS services… credentials of an Identity Access Management (IAM) user… so discovery can operate at the organization level"; bullets on region/account, MID server (optional) and Rotate keys (optional) | CONFIRMED, verbatim | p4 screenshot |
| The form marks Connection name, Access key ID, Secret access key, AWS regions, STS assume role, **Management account ID** and **Amazon CloudWatch log group name** as required (*) | CONFIRMED | Asterisks visible on p5, p7 and p8 |
| **Target account IDs has no asterisk**; "User created in" is a dropdown (Designated account) with no asterisk | CONFIRMED | p5, p7 and p8 screenshots |
| Connection name `TeamSN DTW Hackathon 2026` | CONFIRMED | p5, p7 and p8 screenshots. The p4 narration's speech-to-text renders it "DTV Hackathon 2026". |
| Only "Amazon SageMaker" is legible; the two other checkboxes are cut off | CONFIRMED | p5 and p7: the top two boxes are clipped. Their labels are never shown on any page checked. |
| p7: us-east-1; Target = Management = `273808626098`; STS assume role empty with "Field is required" | CONFIRMED | p7 screenshot |
| **p8: STS assume role = `SgcAictReadOnlyAccessRole` (bare name, not an ARN)**; the label reads "STS assume role", not "ARN" | CONFIRMED | p8 screenshot (greyed form) |
| p8: log group `/aws/bedrock/aict-invocations` | CONFIRMED | p8 screenshot |
| p7 narration: "The assume role should be pre-created. It should be the same for everyone…" | CONFIRMED | Text layer, p7 |
| p5 narration: "You don't need to use a mid-server." | CONFIRMED | Text layer, p5 |
| The access key ID is redacted as `AKIA…XBOO` | CONFIRMED, and correctly handled | The full key ID is visible on p7 and p8. It is not repeated here. |

### A3. The flagged schedule claims (p8–p11)

| Claim | Verdict | Evidence |
|---|---|---|
| "You will have four parent tasks." | CONFIRMED | p8 narration |
| "Connection Successful" and "Import schedules 14" | CONFIRMED | p9 screenshot |
| Four top-level rows (AgentCore-System, Bedrock-Usage, Bedrock-Asset, SageMaker-AI Model), all **Daily / false**, updated 2026-09-30 10:08:51–53 | CONFIRMED | p9 screenshot |
| Child groups Bedrock-Asset (5), Bedrock-Model (1), AgentCore-System (4); 4+5+1+4 = 14 | CONFIRMED | p9 screenshot |
| "activate all of them because so far they are not active… maybe every one hour or so" | CONFIRMED | p9 narration, which continues "…to discover your assets" |
| p10: the AgentCore-System row reads Run = "Periodically", Active = "true" behind the overlay | CONFIRMED | A crop of the p10 row shows both faintly but legibly. Row 2 still reads Daily / false. Only **one** parent is ever shown activated. |
| p11: "Import schedule set.", groups collapsed, Continue enabled, "1 of 3"; "Confirm connection setup" never shown | CONFIRMED | p11 screenshot. p12 is the closing page. |
| "all the child jobs will be active as well" | CONFIRMED as narration only | p11 narration. It is never demonstrated. |
| §3: "Bedrock-Asset (5 children, **one of them the Bedrock-Model group**…)" | **OVERSTATED** | p9 shows Bedrock-Model as its own collapsed group whose parent row is not visible. Nesting it under Bedrock-Asset is a plausible inference (it makes 14 add up), but it is cited as PDF. |

### A4. The flagged template references (all CONFIRMED)

| Ref | Verdict | Content |
|---|---|---|
| L6–7 | CONFIRMED | "No IAM user and no access key is created here or anywhere in this workshop." |
| L29–41 (deviation 6) | CONFIRMED | L37–39 remove "organizations:*, classic Bedrock Agents List/Get, SageMaker List/Describe, unscoped bedrock-agentcore:List*/Get*" |
| L145–146 | CONFIRMED | "a Logs Insights query filtered on eventName="InvokeAgent"" |
| L373 | CONFIRMED | `EnableLogFileValidation: true` |
| L231–232 | CONFIRMED | `VersioningConfiguration: Status: Enabled` |
| L428–433 | CONFIRMED | `StsAssumeRoleArn` = `!GetAtt MemberReadOnlyRole.Arn`, a **full ARN**: "Give this to ServiceNow for the connector's "STS assume role" field". D5's contrast with p8's bare name holds. |
| Other cited lines | CONFIRMED | L48–49, L58–59, L64, L68–74, L79–81, L82–88, L89–93/221/233–239 (7-day retention), L126–134 (single user principal), L162–207 (Allow set and Deny), L189–198, L354–422 (data-only selectors, `IsMultiRegionTrail: false` at L371), L424–440 (4 outputs), L19–21, L27–28 |

### A5. Discrepancy items (PDF and template parts only)

| Item | Verdict | Note |
|---|---|---|
| D1: the PDF requires an IAM user's key; the template says none exists | CONFIRMED | p4 intro; the p5 required fields; TPL L6–7 |
| D2's PDF clause: "the user is in the target account, and Management = Target [p7]" | **OVERSTATED** | p7 shows only Management = Target and "User created in: Designated account". It never shows which account owns the IAM user. By the form's own wording (p4: a user "created in a Designated Member account **rather than** your… management account"), Management = Target would put the user **outside** the target account. Treat the demo values as placeholders; they prove nothing about where the user lives. |
| D4: the three required fields that M11 omits | CONFIRMED | Asterisks on p5, p7 and p8 |
| D4: "the form will not submit with the log group field empty [PDF]" | **OVERSTATED** | This is inferred from the asterisk and the disabled "Create and test connection" button. On p7 the log-group field is empty but shows **no** error; only STS assume role shows "Field is required". Also, TPL L81 ("Discovery works without it") concerns the AWS trail and log-group *resources*, not the form field, so the two are not strictly contradictory: a name can be typed whether or not the group exists. |
| D5 | CONFIRMED | The PDF never says the form prepends an ARN prefix |
| D7: "The PDF never mentions invocation counting" | CONFIRMED for the narration | — |
| §2.2: "The words 'invocation' and 'counting' do not appear in it" | **WRONG (literal, minor)** | "invocations" appears in the p8 screenshot inside `/aws/bedrock/aict-invocations`. Correct reading: neither word appears in the narration, and the PDF never states the log group's purpose. |
| D8, D9, D11, D13, D14 (the PDF quotes) | CONFIRMED | p4/p5 "you…"; p9 Daily/inactive/hourly; p4 "organization level"; p11 team-name prefix; p3 knowledge article |
| D12: the template contradicts itself | CONFIRMED, with a soft OVERSTATEMENT | L35 vs L183 and L40–41 vs L156–161 hold, and L120 "(unchanged permissions and trust)" vs deviation 6 holds. However, L13–14 explicitly excepts deviation 6, so "yet deviations 1–7 exist" is loose; the real conflict there is deviation 5 (an added selector). |

### A6. Unlabelled inferences in A

- L19: "ServiceNow's own AWS account `273808626098`… vendor demo account". The PDF never says whose account it is. Plausible, but not stated.
- p8 row: "Greyed screenshot taken while the test runs". The form is greyed and the cursor is "not-allowed"; "while the test runs" is inferred.

### A7. Content A missed

1. **The integrity caveat (§7(a) INTEGRITY, §7(c)3).** Log-file validation (L373) covers only the S3-delivered trail files and their digests, not the CloudWatch Logs copy `/aws/bedrock/aict-invocations` that §7 recommends querying and citing. Non-current S3 versions also expire after 7 days (L238–239).
2. **More template self-contradictions for D12.**
   - L209 says "(unchanged selectors)", but L414–422 adds a selector.
   - L101 says "Deviations 6 and 7: both values must be set". The header calls that deviation 1 (with 7).
3. **On p7 the empty log-group field shows no validation error.** This bears on D4.
4. **The setup guide's name.** p2 shows the guide is titled "AI Service Graph connector for Amazon - Setup Instructions", and the page says to "prepare your IAM user, roles, and credentials". A captured this, but it also resolves B's naming "discrepancy" (see B5).

---

## Note B: `B-aict-console.md` vs `navigate-ai-control-tower-and-manage-ai-agents.pdf`

### B1. File, instance and date

| Claim | Verdict | Evidence |
|---|---|---|
| 30 A4 pages, react-pdf, 2026-09-30 12:13 CDT | CONFIRMED | pdfinfo |
| 1920×963 screenshots | CONFIRMED | p2–p29. p1 also holds a 1570×1403 image and a 1920×1080 thumbnail. |
| Instance `platformdemoh8.service-now.com` | CONFIRMED | p2 text: "Go to platformdemoh8.service-now.com" |
| Data dated 2026-09-30 | CONFIRMED | Sessions 2026-09-30 (p21–22); runtime chart "Sum for Jul 2026 - Sep 2026" (p15) |

### B2. The flagged claims

| Claim | Verdict | Evidence |
|---|---|---|
| p4: `network_resolution_agent` is Agentic AI, Deployed, Approved, **Managed**, To be determined | CONFIRMED | p4 screenshot |
| p4: `customer_experience_agent` and `it_resolution_agent` have State "-", Status "-", are **Unmanaged**, have no owner, To be determined | CONFIRMED | p4 screenshot |
| p4: the other rows (AICT, AIA, Virtual Agent; Incident Summarization, HR Resume, KB Generator, Ticket Routing; Incident summarization (Generative AI); Test agent TMT) | CONFIRMED | p4 screenshot |
| p4 narration: "pre-created agents in the AWS environment that were discovered before" | CONFIRMED | Text layer, p4 |
| p10: "Unable to show Monitor dashboard. To start seeing the dashboard, you'll need to manage this asset. Managing an asset allows you to get more details about how it's performing." Banner "This asset is currently unmanaged and has limited functionality. Start managing this asset to take action on it and view its data." [Move to Managed] | CONFIRMED, verbatim | p10 screenshot. The banner on p5 and p6 is n/c, though it is page-level on the same asset. |
| p20: "Only managed assets are evaluated." (AI systems 64: Managed 41 / Unmanaged 23) and "Only Agentic AI assets are evaluated." (Agentic AI 60 / Generative AI 4) | CONFIRMED, verbatim | p20 screenshot. The full captions begin "Distribution of AI systems based on provider." and "…by type." The ranking (80/86/86/95/95) and the Quality 95% / Safety 100% figures also match. |
| p21: Evaluated sessions (38), "These sessions are being evaluated based on the established sample rate." | CONFIRMED | p21 screenshot |
| p21: S00000180 = Action Item Extractor 1.0, 1 trace, 98% / 100%, 09:23:38–09:23:39, 1,050 tokens; S00000261 has no AI system, Quality 50%, blank Safety | CONFIRMED | p21 screenshot |
| p22: Answer Relevancy 100% and Secrets Detection 100% (Provider ServiceNow, Level Span, the "judge's reasoning" text); Trace #00000220 at **16:23:38–16:23:39**, 3 spans, 817/233/1050 tokens, Quality N/A, Safety 100% | CONFIRMED | p22 screenshot. The 09:23 vs 16:23 mismatch is real. |
| p25: span tree LangGraph.workflow → model.task → ChatOpenAI.chat, each 1000 ms; AIMessage content "…I'll pass these along to the payroll system now…"; **`"tool_calls": []`**, `"invalid_tool_calls": []`, tags `graph:step:1` | CONFIRMED | p25 screenshot |
| p26: `traceloop_association_properties_session_id` (a UUID) and `traceloop_span_kind: "workflow"`; the System prompt and the User message (a direct deposit request containing account and routing numbers) | CONFIRMED | p26 screenshot. The account and routing numbers are visible unmasked in both the user message and the AI output; they are not repeated here. |
| p26 narration: "in case the tools were called… the whole evidence track is going to be available in this trace" | CONFIRMED | Text layer, p26 |
| p15: "You see the demo data that we loaded here." Runtime tab, "Internal Agents" filter, prompt injection 3 and offensive content 3 "detected and blocked" | CONFIRMED | Text layer and screenshot, p15 |
| p27: "what you need to do first is set up the integration"; p29: "It's where you will set up the connector" and "You're not going to see all those connectors available" | CONFIRMED | Text layer, p27 and p29. §0.10 stitches the two with ellipses, which is acceptable. |
| p28: Connectors / Traces / Multi-instance / Security tabs; Established connections (2) "Test Hackathon 26" and "TMF 2026 Hackathon", Source system "—", Success / Success | CONFIRMED | p28 screenshot |
| p29: six connectors (AI Connector for Amazon, AI Connector for Microsoft, Databricks, GCP Vertex AI, n8n, Salesforce) and the "discovered AI assets appear in your AI asset inventory" text | CONFIRMED | p29 screenshot |
| Other narration quotes (p2, p4, p9, p11, p12, p14, p21–22, p23–24) | CONFIRMED | Text layer |

### B3. OVERSTATED items in B

1. **§0.5: "No AWS-discovered agent appears among the evaluated sessions."** Only 8 of the 38 sessions are visible on p21, and the bar chart shows 5 systems. `network_resolution_agent` is Managed and Agentic (p4), so it would qualify for evaluation under p20's rules. The claim holds only as "none of the 8 visible sessions" (which §1-H states correctly).
2. **§7: "The names also differ: … 'AI Connector for Amazon' vs Module 11's 'AI Service Graph Connector for Amazon'."** PDF A p2 shows ServiceNow's own guided setup titled "AI Service Graph connector for Amazon - Setup Instructions". The two names are the tile name and the product name, so this is not a Module 11 error. (B had not yet read PDF A; its §10 Q9 says so.)
3. **§1 p4 "Managed by = the presenter" and §2.3 "moved to Managed… by the presenter's account".** p4 shows only "Managed by: Alexander…" (AD avatar), while the logged-in user is "Service-now: Alexander Dm…" (SD avatar). "Managed by" is an owner field, as B's own §4 notes, and does not record who performed the move. This is inference, cited as PDF-screen.
4. **§0.7: "Secrets Detection is 100% (safe)" despite bank and routing numbers.** The heading labels this as inference.
   - The PDF never defines the metric's direction or scope. "Safe" is a reasonable reading, given "Safety 100% Good" on p20.
   - Bank and routing numbers are PII, not credentials or secrets, so a 100% score is not clearly a detection miss.
   - The Answer Relevancy and unbacked-action point stands.
   - If this reaches a pitch, rephrase it as "no PII/action-verification metric is shown", not "Secrets Detection missed it".

### B4. Minor fidelity issues in B

- **The p6 narration quote is silently normalised.** The PDF says "if this **reagent** was live… on the **monitor top**". B quotes it as "agent… monitor tab" inside a [PDF-text] quote.
- **§0.1's "the gate for all runtime insight" is slightly broad.** The PDF shows gating for the asset Monitor tab (p10) and for Insights evaluation (p20). The Govern > Security tabs are not shown to be gated.

### B5. Content B missed

1. **Cross-PDF instance gap.** PDF A never names its instance. Its connection "TeamSN DTW Hackathon 2026" is **not** among platformdemoh8's two established connections on B p28. Do not assume the A recording was made on platformdemoh8.
2. **Where Secrets Detection appears.** The trace drawer's "Evaluation scores" (p25–26) lists only Answer Relevancy. Secrets Detection appears only at session level (p22).
3. **The connector naming resolution** from A p2 (see B3 item 2).

---

## Not re-checked (n/c) in this pass

- **A:** the p3 and p6 screenshots (the p6 claim about "us" being typed); the p12 closing page beyond its text layer.
- **B:** the screenshots on p2 (home widgets, 416/259/157), p3 (Inventory All), p5–p6 (asset page and Details, including the banner on p5/p6), p12 (security score 98%, "Amazon 16 agents" agent map), p13 (107 vs 32), p14 (plugin banner) and p16 (heatmap sums to 405). Their text-layer narration was checked.
- **Both:** every LIVE-now, KNOWN, M11 and Team-notes claim.
