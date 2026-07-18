VERIFY: demo-dev re-repro post-fix   METHOD: live-probe   ENV: demo-dev
RESULT (from world.yaml): "after DAC fix: demo-dev POI panel loads, 200 OK, locations render. GREEN."
CONDITIONS: same as repro (standard load, same advertiser/session)
PRE: 500/fetch-failed (1/1)
POST: 200 OK, locations render (0 failures, 1/1 green)
DETERMINISTIC: true (pre was k=n=1, consistently broken)
EXIT-VERIFY: deterministic path — single clean same-condition green pass = sufficient
