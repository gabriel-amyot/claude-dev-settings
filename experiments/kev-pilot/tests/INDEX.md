# Offline tests

- [test_local_client.py](test_local_client.py): Transport, metadata, numeric validation, and process boundaries.
- [test_retrieval.py](test_retrieval.py): Source integrity, alias parity, and discriminative sparse-label metrics.
- [test_pilot.py](test_pilot.py): Receipt accounting, recovery, packet admission, and unknown evidence handling.
- [test_probes.py](test_probes.py): Authored probe construction, permutations, and isolation comparisons.
- [test_study.py](test_study.py): Bounded execution, exact-instance cleanup, and study-owned evidence aggregation.

These tests use temporary fixtures and fake local HTTP servers. They do not establish native inference speed or recall quality.
