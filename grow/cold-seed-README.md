# Cold seed for grow run 001 (map-2 environment, presented cold)

Contents: source_items.json (the raw export) + the write-protection wall on
it (an ENVIRONMENT property — the product protects intake artifacts).

Deliberately absent: migration.json and any .dotmaps config — those are
COMPILE OUTPUTS, i.e., map material. Including them would leak the withheld
answer key's structure (required fields, target name) into the environment.
The agent must discover structure by poking, not read it from a config.
