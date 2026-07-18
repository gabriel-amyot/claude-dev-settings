"""Service Factory — shared gate library.

Pure functions used by every gate script AND by the eval harness. No I/O side
effects beyond reading fixture files. Everything here is mechanically decidable
(NP1: presence checks are not enough — these encode the materiality/relevance
predicates the red-team demanded).

Run `python3 lib.py` to execute the self-tests.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


# ---------------------------------------------------------------------------
# Enums (spec §4). Fixed vocabularies — an out-of-enum value is a gate reject,
# never an LLM sentiment call (D6).
# ---------------------------------------------------------------------------
STAMPS = frozenset({"OBSERVED", "INFERRED", "REPORTED", "ASSUMED"})
CARD_STATUS = frozenset(
    {"UNTESTED", "CONFIRMED", "REFUTED", "INCONCLUSIVE", "REVIVED", "SHELVED"}
)
METHODS = frozenset(
    {"live-probe", "log-trace", "exhaustive-read", "red-test", "ui-probe"}
)
COST = frozenset({"S", "M", "L"})
LIKELIHOOD = frozenset({"low", "med", "high"})
STRENGTH = frozenset({"strong", "weak"})
ORIGINS = frozenset(
    {"playbook", "hunch", "differential", "scout", "express", "library"}
)
LAYERS = ("ui", "backend", "data", "db", "infra")

# Methods that only establish a symptom on a surface (IFM-2): they cannot back
# a mechanism-class cause on their own.
SYMPTOM_METHODS = frozenset({"ui-probe"})
# Methods that establish a mechanism directly (IFM-2 accept set).
MECHANISM_METHODS = frozenset({"log-trace", "exhaustive-read", "red-test"})

# Domains a component can belong to. A mechanism-class cause is one scoped to a
# non-ui domain — it needs mechanism-grade evidence, not a symptom read.
MECHANISM_DOMAINS = frozenset({"data", "db", "backend", "infra", "config"})


# ---------------------------------------------------------------------------
# YAML / file helpers
# ---------------------------------------------------------------------------
def load_yaml(path):
    """Load a yaml file; return {} for empty, raise for missing/bad."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("pyyaml is required for the service-factory gates")
    p = Path(path)
    data = yaml.safe_load(p.read_text()) if p.exists() else None
    return data if data is not None else {}


def read_text(path):
    p = Path(path)
    return p.read_text() if p.exists() else ""


# ---------------------------------------------------------------------------
# Domain classifier (D5/D6). Keyword rules over a component git-ref or a source
# instance name. Order matters: most specific first.
# ---------------------------------------------------------------------------
def domain_of(name: str) -> str:
    """Map a component/source label to a stack domain. Deterministic."""
    if not name:
        return "unknown"
    n = str(name).lower()
    # config / wiring first — a config allowlist must not read as data.
    if any(k in n for k in ("config", "wiring", "allowlist", "env-var", "envvar")):
        return "config"
    if any(k in n for k in ("bigquery", "bq", "dataform", "dataset", "-data", "data-")):
        return "data"
    if any(k in n for k in ("mysql", "liquibase", "-db", "database", "sql")):
        return "db"
    if any(
        k in n
        for k in ("dac", "iac", "terraform", "infra", "mig", "cloud-run", "cloudrun", "cos")
    ):
        return "infra"
    if any(
        k in n
        for k in ("front", "portal", "-ui", "react", "mapbox", "component", "panel")
    ):
        return "ui"
    if any(
        k in n
        for k in ("backend", "-ms", "service", "-report", "-explorer", "api", "adapter")
    ):
        return "backend"
    return "unknown"


def is_mechanism_component(component: str) -> bool:
    return domain_of(component) in MECHANISM_DOMAINS


# ---------------------------------------------------------------------------
# Claim stamps. Load-bearing claim lines must carry a stamp citing a ledger row.
# ---------------------------------------------------------------------------
_STAMP_RE = re.compile(
    r"\[(OBSERVED|INFERRED|REPORTED|ASSUMED)\b([^\]]*)\]", re.IGNORECASE
)
_OBS_ID_RE = re.compile(r"\bO\d+\b")


def parse_stamps(text: str):
    """Return list of (stamp, detail, cited_obs_ids) for a line/block."""
    out = []
    for m in _STAMP_RE.finditer(text or ""):
        stamp = m.group(1).upper()
        detail = m.group(2).strip()
        ids = _OBS_ID_RE.findall(detail)
        out.append((stamp, detail, ids))
    return out


def has_observed_citation(text: str) -> bool:
    for stamp, _detail, ids in parse_stamps(text):
        if stamp == "OBSERVED" and ids:
            return True
    return False


# ---------------------------------------------------------------------------
# Source signature (IFM-15). Two observations with the same signature are ONE
# signal — they cannot both count toward "independent" strength.
# ---------------------------------------------------------------------------
def source_signature(obs: dict) -> tuple:
    src = obs.get("source", {}) or {}
    return (
        src.get("env"),
        src.get("instance"),
        src.get("traffic"),
        src.get("window"),
    )


# ---------------------------------------------------------------------------
# Scope covering (F07/F17). A verdict may REFUTE a card only if its scope
# covers the card's scope. Env is the discriminating axis.
# ---------------------------------------------------------------------------
def _as_env_set(scope: dict):
    if not scope:
        return set()
    env = scope.get("env")
    if env is None:
        return set()
    if isinstance(env, (list, tuple, set)):
        return set(env)
    return {env}


def scope_covers(verdict_scope: dict, card_scope: dict) -> bool:
    """True if verdict_scope ⊇ card_scope on the env axis."""
    card_envs = _as_env_set(card_scope)
    verdict_envs = _as_env_set(verdict_scope)
    if not card_envs:
        return True
    return card_envs.issubset(verdict_envs)


# ---------------------------------------------------------------------------
# Statistics for the flaky exit standard (IFM-4). Pure-python regularized
# incomplete beta + Clopper-Pearson lower bound + required-N.
# ---------------------------------------------------------------------------
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3.0e-12, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def betainc_inv(a, b, y):
    """Inverse of I_x(a,b) in x for a target y, via bisection."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if betainc(a, b, mid) < y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson_lower(k, n, alpha=0.05):
    """One-sided (1-alpha) lower confidence bound on p given k/n.

    Conservative failure-rate estimate: the SMALLEST plausible p, which forces
    the LARGEST required N at exit (IFM-4). k=3,n=10,alpha=0.05 -> ~0.087.
    """
    if k <= 0:
        return 0.0
    if k >= n:
        return alpha ** (1.0 / n)  # exact for k==n
    return betainc_inv(k, n - k + 1, alpha)


def required_n(p_lower, target=0.05):
    """Smallest N so that (1 - p_lower)^N <= target."""
    if p_lower <= 0.0:
        return math.inf
    if p_lower >= 1.0:
        return 1
    return math.ceil(math.log(target) / math.log(1.0 - p_lower))


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------
def _selftest():
    assert domain_of("bq-data") == "data"
    assert domain_of("config-file") == "config"
    assert domain_of("dac-config") == "config"  # config wins over dac/infra
    assert domain_of("frontend") == "ui"
    assert domain_of("proxrp-cos") == "infra"
    assert domain_of("app-proximity-report") == "backend"
    assert is_mechanism_component("bq-data") is True
    assert is_mechanism_component("frontend") is False

    assert has_observed_citation("cause X [OBSERVED O7]") is True
    assert has_observed_citation("cause X [INFERRED from O7]") is False
    assert has_observed_citation("cause X [ASSUMED]") is False

    assert scope_covers({"env": ["demo-dev", "demo-prod"]}, {"env": "demo-dev"}) is True
    assert scope_covers({"env": "demo-prod"}, {"env": ["demo-dev", "demo-prod"]}) is False

    assert source_signature({"source": {"env": "d", "instance": "i", "traffic": "t"}}) == (
        "d", "i", "t", None,
    )

    # Beta sanity: median of Beta(3,8) ~ 0.26; I_0.273(3,8) ~ 0.5-ish.
    assert abs(betainc(3, 8, 0.087) - 0.05) < 0.01, betainc(3, 8, 0.087)
    pl = clopper_pearson_lower(3, 10, 0.05)
    assert 0.08 < pl < 0.095, pl
    assert required_n(pl) == 33, required_n(pl)
    # k==n exact branch
    pl2 = clopper_pearson_lower(10, 10, 0.05)
    assert 0.7 < pl2 < 0.75, pl2
    print("lib.py self-tests OK  (p_lower(3/10)=%.4f, required_N=%d)" % (pl, required_n(pl)))


if __name__ == "__main__":
    _selftest()
