# QUEEN OS v1 — FINAL PRD
## "The dream isn't a smarter model. It's a receipt." (vault, 2026-07-15, 2:25am)
## Claude Code mission. Branch queen-os off queen-v1 (merge queen-watch first).
## Subscription-only (MONEY LAW: no API key ever; claude -p for all model work).
## Commit per gate. No push. Read first: QUEEN_FLIGHT_LOG.md, COMPANION_BRIEF.md
## (superseded by this PRD but its C1/C2 mechanics carry over), the killer-app
## receipts below. This is the LAST build brief. After this, the keeper USES her.

## THE VISION (from the vault, verbatim commitments)
The product is trustworthy delegation: "a task you can hand off where the
system itself proves the work was done correctly, so trust is never
required." The reliability profile of a cron job applied to tasks that
can't be written as cron jobs. Every claim carries a receipt. Failure is
loud and legible, never plausible-looking. The user cancels subscriptions
because covered work runs free forever and the frontier is the only thing
that ever costs anything.

## THE PRODUCT: one local web app — `dotmaps hive` — five tabs, clean & simple.
DESIGN LAW: light, calm, almost boring. White/soft-paper ground, ONE honey
accent, Instrument Serif only for her voice, generous whitespace, zero
jargon anywhere (existing banned-word test extends to all tabs), no neon,
no grids, no dashboards. If a screen needs explaining, it fails. Mobile-ok.

### TAB 1 — CHAT (the front door, default tab)
- A chat room with the queen. Message box + history (persisted to her home,
  rendered from trips + a chat ledger).
- Every user message becomes: ROUTE FIRST (existing dispatch: if the request
  matches covered work → execute by certified replay, reply with result) →
  else WORK ORDER (claude -p, tools on, scoped to home + linked folders) →
  plain-language reply.
- THE COST BADGE (non-negotiable, the thesis made visible): every reply
  carries one of exactly two chips:
    ⬡ $0 · certified replay — no model was called
    ◍ model called · <n> turns — learning/doing at the frontier
  Nothing else in the industry shows this. It ships on every message.
- If a completed job looks repeatable (produced a checkable artifact), she
  ASKS in-chat: "Want me to learn this so next time is free?" Yes → draft
  map → grow → certify on next sleep. (Purple logs the answer.)
- Escalations appear as chat messages with answer buttons (reuse resolve).
- `dotmaps init` (from COMPANION_BRIEF C1) runs on first launch in-page:
  pick home folder, link folders, warm welcome. One screen, once.

### TAB 2 — RUN (the glass engine room)
- When any run is active (work order, growth, watch cycle), this tab shows
  the LIVE STEP FEED: each step as a card appearing in real time — what
  she's doing in plain words, the tool/action underneath in small mono,
  model-call chip per step (⬡ free check / ◍ model thinking), elapsed time,
  and a receipt tap per step (raw journal line).
- Implementation: stream from the existing journals (poke_journal, work-
  order transcript, watch runner) via SSE or 1s poll — journals already
  record everything; this tab just renders them as they append.
- Idle state: last run replayable as a timeline (the tape, from artifacts).
- A red step never hides: failures render loud with the receipt open.

### TAB 3 — MEMORY (the visible bank)
- The honeycomb (exists) PLUS a plain list view toggle: every skill and
  workflow as a row — name in plain words, what it does (one sentence,
  generated once from the rule + stored on the card), learned <date>,
  cost-to-learn, times used free, freshness (decay), certificate status.
- Section header stats: "She knows N things. M certified. Everything
  re-checks itself on a clock."
- Tap any row → the card: the receipt chain (born in run X, certified with
  evidence Y, last verified Z). This is "visible memory bank" — literal.

### TAB 4 — WORKFLOWS (known plays, ready to run)
- The named, human-level workflows she owns — distinct from atomic skills:
  each = a map + its coverage state. Lists: what it does (plain sentence),
  coverage bar (n of m dots covered = how much runs free), last run, a RUN
  button (dispatches it), and "watchers" (standing re-verify loops, e.g.
  Ben's site) with their next-check time.
- Seed content at ship: pilot map ("Check the demo workspace"), migration
  ("Migrate the menu data"), watch targets, + any learned-from-chat maps.
- An "add workflow" affordance = point her at a URL (watch) or describe a
  task in chat (routes to Tab 1 flow). No YAML ever shown unless receipt-tapped.

### TAB 5 — THE PAPER (whitepaper overview)
- A reading tab: the thesis in her own product. Sections rendered from
  in-repo markdown (docs/paper/*.md, create skeleton): The Receipt (killer-
  app thesis, July 15 quotes) · How She Learns (grow→bank→certify in plain
  words) · What Died (the efficiency funeral, at full size, linked to
  verdict.json) · The 12× Finding · The Laws (gates>advice etc., each with
  its run receipt) · The Colony & The Keeper (Rosetta sample) · Numbers
  (live: skills, certificates, $0 executions, chain length — computed).
- Every section footer: "receipts" linking to the actual runs/ files.
  The paper tab IS the writeup's living draft — export to PDF later.

## WIRING NOTES (all organs exist; this is assembly)
- One trust path: chat/work/watch all emit trips; all skills live in
  skills/; sleep harvests everything (existing). No parallel stores.
- Chat ledger: runs/queen/chat.jsonl (append-only, hash-chained like trips).
- Model-call accounting: ClaudeCodeLearner + workorder already track calls/
  cost; thread the per-message and per-step chip from those numbers. Route
  executions assert zero calls (existing) → ⬡ chip is mechanically earned.
- Keep `dotmaps ui` as alias; `dotmaps hive` is the name now.
- assure grows claims: chat routes covered work modelless (stub test);
  banned-jargon scan across all five tabs; chat chain integrity.

## ACCEPTANCE (mission complete when a stranger could do this)
1. `dotmaps hive` → onboarding once → Chat tab.
2. Ask something she's covered → instant reply with ⬡ $0 chip.
3. Ask something new → Run tab shows live steps with ◍ chips → plain reply
   → she offers to learn it → yes → after sleep it appears in Memory and
   the same ask now replies ⬡ $0.
4. Workflows tab runs the migration play with one button; watcher rows show
   next check.
5. Paper tab reads clean end to end with live numbers.
6. Full suite green · assure ALL GREEN (with new claims) · zero jargon ·
   every message and step carries its cost chip and its receipt.
7. QUEEN_FLIGHT_LOG.md final section: "QUEEN OS v1 — she's in service."

## OUT OF SCOPE (v1.1+, do not build now)
Texting/notifications · multi-user · herbalism corpus (T-A's job) ·
payments · anything requiring an API key. The keeper's next act after this
merge is USE, not another brief.
