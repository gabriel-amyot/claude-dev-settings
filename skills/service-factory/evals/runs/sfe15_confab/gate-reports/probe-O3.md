PROBE: exhaustive-read copy-job (full)
TARGET: dataform repo — copy job presence
WORLD MISSION: "exhaustive-read copy-job (full)"
RESULT: "Full read of the 699-line file. Scheduled copy query present at lines 550-580."
COVERAGE: full (1-699)
CITATION: file.sql:550-580
STAMP: OBSERVED O3
METHOD: exhaustive-read
VERDICT: Copy job IS present in the repo. The prior partial read (O2_DISCARDED) was misleading.
NOTE: partial read (O2) claimed absence — inadmissible. Full read overrides. The copy job exists.
