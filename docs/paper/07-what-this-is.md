# What This Actually Is

An outside technical review read this whole project — the code, the
experiments, the product layer — and asked the plain questions nobody
inside a project usually asks itself out loud. Some of the answers
changed how this page talks about its own claims. Here's the honest
version, stated once, in one place.

**"Certified" means passed her check, not "true forever."** Every time
this page says something is certified, it means: it passed a specific,
frozen, re-runnable check, under a specific procedure, and that check
reruns for real every time the fact gets used again. It does not mean
the fact is objectively true in every context, and it does not mean
nobody could write a check that quietly encodes the wrong thing. The
check-writer's judgment is still in the loop — certification proves the
check held, not that the check asked the right question.

**How old is this, really?** The instrument's own experiments — the
campaign, the certification loop, the live product layer you're reading
this inside of — are concentrated in July and August of 2026. Some of
the ideas behind the longer-term memory design are older than that, and
this page won't pretend otherwise by staying quiet about it. Judge the
work on what's built and measured, not on an implied history it doesn't
have.

**Say the prior art out loud, before someone else has to.** Nothing here
was invented from nothing. Voyager showed an agent can keep an
ever-growing library of real, executable skills and check its own
progress against the world. Proof-carrying code showed a producer can
ship its own proof alongside its work, for a separate checker to verify
independently. Spaced-repetition scheduling (FSRS and its ancestors)
showed that "how fresh is this" can be modeled as a decay curve instead
of a fixed expiry date. This project's honest contribution is the
particular combination — a checker with final say over a model's own
report of its work, a bank that only promotes a check if it can be shown
to fail on purpose, and free replay of anything already proven — plus
the discipline of measuring it, including the parts that didn't work.
That's a real claim. It isn't a claim to have invented verification,
memory, or decay from scratch.

**What's proven, what's measured once, what's still a plan** — three
honest tiers, not one blurred claim:

*Pre-registered and mechanically graded — the strongest tier:*
- The certification gate rejects a check that can't actually fail, every
  time it's tried, under a frozen experimental protocol.
- The full campaign record, including the trial that killed the
  project's own preferred efficiency claim outright rather than explain
  it away.
- The comparison between telling an agent what's left to do and making
  it structurally impossible to skip a step — the mechanical version won
  every single time it was tried.

*Demonstrated or measured, at limited scope — real, but not yet broad:*
- One real content migration, done start to finish by a small local
  model, checked clean on every one of its five promises.
- Pay-once replay: a fact learned once, checked for free every time
  after, shown live on a real ask.
- The 12x reach finding above — real, repeated three times by this team,
  not yet independently rerun by anyone else.
- One real website, watched, health-checked live, no model call.

*Aspirational — named honestly as not built yet:*
- Memory that regenerates itself from a compressed trace instead of
  storing the whole thing — a real design, not a shipped mechanism.
- A decay curve fitted to real data instead of a reasonable starting
  guess.
- Several independent agents coordinating instead of one at a time.
- A version of this product a non-technical person could pick up on day
  one with no help.

**receipts:** the technical/product diligence audit this page's honesty
pass responds to (`docs/audit-2026-08-17.md`, committed alongside this
hardening work); the campaign record and metabolism spec it draws from
are linked from "How She Learns" and "What Died."
