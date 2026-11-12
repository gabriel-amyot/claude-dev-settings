# Database schema

- 001.sql: Strict domain tables, constraints and immutable event protections.

Schema version is checked by store.py. New schema changes require a numbered migration and compatibility tests. Do not modify the live database with ad hoc SQL.
