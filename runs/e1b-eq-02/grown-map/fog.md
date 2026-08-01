# Fog — declared honestly by the grow loop

- migration.json's required_fields array has exactly 3 entries: title, price, date — no confirming poke after forage (2026-07-31T23:06:12)
- source_items.json item with slug 'spring-junior-clinic' has body exactly 'See also <a href="/summer-scoring-camp">summer camp</a>.' — no confirming poke after forage (2026-07-31T23:06:43)
- source_items.json item with slug 'spring-junior-clinic' has body exactly 'See also <a href="/summer-scoring-camp">summer camp</a>.' — no confirming poke after forage (2026-07-31T23:07:12)
- source_items.json item with slug 'spring-junior-clinic' has body containing exact text 'See also <a href="/summer-scoring-camp">summer camp</a>.' — no confirming poke after forage (2026-07-31T23:07:24)
- target_items.json now contains an empty JSON array after being written — no confirming poke after forage (2026-07-31T23:13:26)
- target_items.json write is not validated against required_fields; writing an item missing 'price' still succeeds and is stored without it — no confirming poke after forage (2026-07-31T23:13:37)
- migration.json is not protected like source_items.json; it can be overwritten with arbitrary non-JSON text like 'test' and read back exactly — no confirming poke after forage (2026-07-31T23:13:47)
