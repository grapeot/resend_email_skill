---
name: suppression-analysis
description: Analyze Resend suppression lists, calculate deliverability metrics and bounce rates, classify bounces and spam complaints, trace originating emails via source IDs, mine post-suppression attempts, discover typo-rescue pairs, and generate actionable operator reports. Load when the user asks for suppression, bounce, complaint, or deliverability analysis.
---

# Suppression List Analysis Skill

## Purpose & Deliverable

Analyze team-wide Resend suppression records to evaluate deliverability health, identify configuration or application bugs, separate spam complaints from routine delivery failures, and evaluate reset candidates.

When instructed to inspect or analyze suppressions, produce a single Markdown report named `suppression_report_<YYYY-MM-DD>.md` in the current working directory. The primary audience is the operator. Because suppression lists contain private recipient addresses, treat this file as confidential data and never commit it to git.

For core CLI syntax, credentials, and safety flags, reference the canonical skill in `skills/skill_resend_email.md`.

## Data Collection

Collect the full suppression inventory and recent sent email records:

```bash
# Export all current team-wide suppressions
.venv/bin/python -m resend_email_skill.cli suppressions list --all --limit 100 --format json > suppressions_snapshot.json

# Fetch recent sent email records for denominator calculation.
# The send log is not wrapped by the CLI; call the Resend API directly with the same key:
#   curl -s -H "Authorization: Bearer $RESEND_API_KEY" "https://api.resend.com/emails?limit=100&after=<cursor>"
# Response shape: {"object":"list","has_more":true,"data":[{id, to, from, created_at, subject, ...}]}
# Paginate with after=<last id> until has_more=false. Retention is roughly 30 days.
```

Each suppression record contains `email`, `origin` (`bounce`, `complaint`, or `manual`), `created_at`, and `source_id`.

## Seven Analysis Dimensions

### 1. Funnel Overview
Quantify the total suppression count, monthly distribution, and breakdown across origins (`bounce`, `complaint`, and `manual`).
- Track month-over-month trajectory to identify whether suppression growth is flat, steady, or spiking.
- Establish the baseline distribution before drilling into specific suppression classes.

### 2. Denominator (Bounce Rate)
Compute the true deliverability bounce rate within the observable send window:
- Query send volume from `GET https://api.resend.com/emails` across the provider retention window (~30 days). Paginate with `after=<last id>` until `has_more` is false.
- Calculate: `bounce_rate = (new_bounces_in_window / sends_in_window) * 100%`.
- If the send-log window does not cover the suppression window (historical entries older than ~30 days), explicitly state that denominator data is unavailable. Report absolute counts only. Never fabricate or extrapolate a rate without send logs.

### 3. Complaint Class
Always analyze complaints (`origin == "complaint"`) separately from bounces:
- Complaints occur when a recipient clicks "Report Spam", signaling explicit negative user sentiment. Accidental delivery failures do not generate complaints.
- Compare the complaint rate against the industry red-line threshold of ~0.1% (1 per 1,000 sends) enforced by major mailbox providers.
- For every complaint (or up to 5 if volume is high), perform a deep dive: trace `source_id` via `GET /emails/:id` to record the recipient, timestamp, subject line, and email category (verification code, system notification, marketing broadcast).

### 4. Bounce Classification (Heuristic)
Bounces arise from distinct failure modes. Group them heuristically into three buckets:
- **Apparent typos / malformed**: Addresses with common domain misspellings (e.g., `@gamil.com`, `@yaho.com`), malformed syntax, wrong `@` symbol counts, or obviously invalid local parts. These are honest input mistakes; the mailbox cannot receive mail, so resetting them is pointless.
- **Internal / own-domain**: Addresses hosted on the operator's own domains (e.g., test or staging mailboxes). Exclude these from public delivery health assessments.
- **Genuine hard bounces**: Remaining real mailboxes rejected due to deleted accounts, full mailboxes, or disabled MX hosts. This group forms the pool of potentially recoverable addresses for reset evaluation.

For each bucket, report the total count and 3–5 representative example addresses (redacted for privacy).

### 5. Conclusions (Three Fixed Questions)
Every report must conclude by answering three mandatory questions:
1. **Is there a systemic delivery problem?** (e.g., domain-wide blocks, authentication failures, broken DNS records).
2. **Is anything urgent?** (e.g., new spam complaints, sudden volume surges, bounce rates exceeding thresholds).
3. **Are there reset candidates?** Identify eligible genuine bounces for potential unsuppression. Prefer addresses with evidence of life (post-suppression attempts, typo-rescue pairs) over blind resets; users often return on their own without dedicated re-send campaigns. Spam complaints are **never** reset candidates.

### 6. Post-Suppression Attempts
Mine the send log for addresses blocked at send time after listing (`last_event == "suppressed"`):
- **Detection & Cross-reference**: Collect sends with `last_event == "suppressed"` from `GET /emails` and compare timestamps against suppression snapshot `created_at`. Identify sends blocked because the address was already suppressed.
- **Still-Knocking Pattern**: A user who bounces once on a typo and retries within minutes from a signup form gets silently blocked. Rapid retries signal locked-out legitimate users rather than dead addresses.
- **Reporting & Reset Priority**: Report blocked attempt counts, unique addresses, and per-address retry timelines. These represent high-priority reset candidates; because users return spontaneously, recovery requires no outbound test campaign.

### 7. Typo-Rescue Pairs
Match genuine hard bounces against delivered send-log recipients using edit distance:
- **Pair Discovery**: Compare bounce addresses against all send-log recipients using `difflib.SequenceMatcher` (same domain with local ratio > 0.8; or similar domain ratio > 0.92 with matched local). Confirm the close-spelling address has `last_event == "delivered"`. If both bounced, exclude both.
- **Pattern Classification**: Report `bounce_address ↔ rescued_address`, similarity scores, and error patterns (omitted letters, transpositions, domain typos like `mail.com` -> `gmail.com`, pasted phone numbers).
- **Tombstone Semantics**: Rescued entries are harmless tombstones (~20% of genuine bounces in real data) where users self-recovered. They are safe to reset, and their frequency motivates upstream signup-form validation ("did you mean gmail.com?").

## Source-ID Tracing

Use `source_id` to retrieve originating email payloads via `GET https://api.resend.com/emails/:id`:
- **Complaints**: Trace every complaint (up to 5 if many) to determine the exact message that provoked the spam report. Note that when a user accidentally mistypes an email address during registration, the unintended legitimate mailbox owner receives the message and may report it as spam.
- **Bounces**: Sample up to 5 bounce entries across categories to identify which application flows triggered the rejection (e.g., auth codes vs. system alerts).
- **Suppressed Attempts**: Scan the send log for `last_event == "suppressed"` entries and cross-reference suppression entry dates to reveal legitimate users locked out after an initial typo.

## Deliverable Report Skeleton

The deliverable `suppression_report_<YYYY-MM-DD>.md` must follow this exact structure:

```markdown
# Suppression Analysis Report - <YYYY-MM-DD>

## TL;DR
- **Volume & Trend**: [Total count, 30-day delta, trajectory assessment]
- **Complaint Status**: [Total complaints, complaint rate vs 0.1% threshold]
- **Classification Highlights**: [Counts of typos vs internal vs genuine bounces]

## Funnel Overview
| Metric | Count | Share |
|---|---|---|
| Total Suppressed | ... | 100% |
| Bounce | ... | ...% |
| Complaint | ... | ...% |
| Manual | ... | ...% |

*Monthly distribution table...*

## Denominator (Bounce Rate)
- Send log observation window: [Start Date] to [End Date]
- Total sends in window: [Count]
- Net new suppressions in window: [Count]
- Calculated bounce rate: [X.XX%] (or "Denominator unavailable; reporting absolute counts only")

## Post-Suppression Attempts
- Blocked attempts (`last_event == "suppressed"`): [Count] across [N] unique addresses
- Still-knocking candidates (real users locked out by post-listing retries):
  - `us***@example.com`: suppressed at [Timestamp] -> [N] blocked retries within [Window] (e.g., signup flow)

## Classification Detail
- **Apparent Typos** (Count: N): `ex***@gamil.com`, ...
- **Internal / Own-Domain** (Count: N): `test***@example.com`, ...
- **Genuine Hard Bounces** (Count: N): `user***@example.com`, ...
- **Typo-Rescued** (Count: N): `bounc***@example.com` ↔ `rescu***@example.com` pairs with delivered confirmation.

## Deep Dives (Max 5)
1. **Recipient**: `us***@example.com` (Origin: complaint, Source ID: `<uuid>`)
   - Subject: "Your verification code" | Timestamp: 2026-09-01 | Type: Auth
   - Root Cause: Likely recipient misentry during signup; real owner marked as spam.

## Conclusions
1. Systemic delivery problem: [Yes/No + rationale]
2. Urgent issues: [Yes/No + details]
3. Reset candidates: [Prioritize entries with evidence of life (post-suppression attempts, typo-rescues) over blind resets; no campaign needed as users return organically; 0 complaints]

## Data Snapshot & Audit
- Snapshot timestamp: <ISO-8601>
- Commands used: `suppressions list --all --limit 100 --format json`
```

## Reset Candidate Review & Operator SOP

After presenting the report, ask the operator whether to reset the eligible resettable classes (never complaints).

If the operator grants explicit authorization, follow this Standard Operating Procedure:

1. **Create Backup**:
   Save the full suppression snapshot and the candidate removal list to local uncommitted JSON files:
   ```bash
   cp suppressions_snapshot.json suppressions_backup_<YYYYMMDD>.json
   # Write selected removal targets to reset_candidates_<YYYYMMDD>.json
   ```

2. **Execute Reset with Two-Phase Safety Gates**:
   First, perform a batch dry-run pass over all candidate addresses:
   ```bash
   .venv/bin/python -m resend_email_skill.cli suppressions remove user@example.com --dry-run --format json
   ```
   After verifying the dry-run output, execute removal one address at a time using `--confirm-remove`:
   ```bash
   .venv/bin/python -m resend_email_skill.cli suppressions remove user@example.com --confirm-remove --format json
   ```

3. **Audit Logging & Verification**:
   - Save execution results (successes and failures) to `suppression_removal_audit_<YYYYMMDD>.json`.
   - Verify complaint records remain in the suppression list. If any complaint was touched, re-add it immediately via `suppressions add <email> --confirm-add`.

4. **Recipient Re-Bounce Notice**:
   Removing an address from the suppression list does not fix the destination mailbox. If an address remains broken, subsequent sends will bounce and automatically re-enter the suppression list.

## Known Caveats & Operational Lessons

- **Team-wide Scope**: Resend suppressions apply across the entire team account, affecting all sending domains.
- **Send-Log Retention Limits**: The `/emails` endpoint retains logs for roughly 30 days. Historical bounce rates beyond this window cannot be computed; report absolute counts instead.
- **No Signal Without Subsequent Sends**: Removing an address produces zero delivery signal on its own. Evaluating recovery requires a deliberate re-send followed by approximately one week of observation. Permanent typos will bounce immediately, whereas recovered mailboxes will succeed.
- **Verification Code Contexts**: In verification code flows, bounces typically represent honest user mistakes (typos, abandoned accounts, full mailboxes) rather than intentional user rejections.
- **Suppressed Attempt Telemetry**: Suppressed attempts are recorded in the send log with `last_event: "suppressed"`; cross-referencing them with suppression entry dates distinguishes real users still trying (retry shortly after listing) from dead addresses with no further attempts.
- **Typo-Rescue Quantification**: Edit-distance matching of bounce addresses against the delivered send log quantifies typo-rescues (users who mistyped, self-corrected, and eventually received mail); a meaningful share (~20% in real data) of genuine hard bounces can be typo tombstones. The actionable fix is upstream: add email-spelling confirmation to the signup form.

## Privacy Boundaries

- **Private Recipient Data**: Suppression lists contain confidential email addresses. Never commit snapshots, export files, audit logs, or generated markdown reports to version control.
- **Mandatory Dry-Run**: Always run removal commands with `--dry-run` before requesting operator confirmation.
- **Explicit Authorization**: Never add or remove suppressions without unambiguous operator approval.
- **Strict Complaint Protection**: Complaints must never be reset; doing so damages domain sender reputation.
