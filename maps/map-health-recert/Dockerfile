# Pinned verifier environment for map 1 — the portability moat (spec §4.1).
# A dot verifies identically on any machine because this image is the machine.
# The workspace is bind-mounted READ-ONLY at /ws when verifiers run.
#
# HTTP dots (002-005, 007, 008) need only stdlib Python. The browser/perf dots
# (006 no-console-errors, 009 lighthouse) need Chromium + node tooling, pinned
# here so those checks pass in-container and error cleanly outside it.
# Pin to bookworm: playwright's `--with-deps` references font packages
# (ttf-unifont, ttf-ubuntu-font-family) that were removed in Debian trixie,
# which is what the unqualified `-slim` tag now resolves to.
FROM python:3.11-slim-bookworm

# --- Node + Chromium for the browser-dependent dots ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Playwright (dot 006) + Lighthouse (dot 009), version-pinned.
RUN pip install --no-cache-dir playwright==1.48.0 \
    && playwright install --with-deps chromium \
    && npm install -g lighthouse@12.2.1

WORKDIR /map
