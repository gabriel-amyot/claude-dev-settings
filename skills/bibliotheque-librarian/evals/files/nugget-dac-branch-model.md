# Nugget: DAC repo branch / deploy model

**Source:** SPV-165 overnight crawl (2026-04-21)

DAC repos on GitLab have three branches that map to environments: `dev`, `uat`, `main` (prod). Each branch auto-deploys on push. ALL changes go to `dev` first. Promotion is a manual forward-merge: dev -> uat -> main. Agents never push directly to `main` or `uat`. Hotfixes to uat/main are always human-initiated.

The incident that produced this: a change was pushed to `main` expecting it to deploy, but the pipeline that actually served the environment ran from `dev`, so the change never reached the running service.
