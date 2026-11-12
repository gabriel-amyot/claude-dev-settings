# BMAD loading checks

Run `python3 -m unittest discover -s ~/.claude-shared-config/bmad/tests -v`.
Checks cover project config precedence, neutral defaults, missing-source errors, resource boundaries,
custom roster membership and reversible/idempotent installation under another home path.
