# Blast radius — map 3 (health re-certification)

Every dot is read-only (HTTP GET, DNS lookup, headless page load). There is no
build, no deploy, no form POST, no filesystem mutation, no credential use.

**Worst case:** the scheduled runs add trivial read traffic to the production
site (a handful of GETs + one headless page load per cadence tick). Mitigation:
the cadence is coarse (default every 6h) and the request volume is bounded by
the sitemap page count. Nothing here can damage the deployment.

This is the safest map in the set — which is why it is the natural recurring
subscription product.
