# Python HTTP Client Egress Gotchas

Cross-org. Two ways a "this request cannot leave the machine" claim turns out to be false.

**Source:** Klever session `ttd-validation-ladder`, 2026-08-13. Found by an adversarial Codex review
of a loopback exemption, which refuted the claim the whole design rested on.

---

## `httpx` Trusts Proxy Environment Variables by Default

Any "this request cannot leave the machine" claim is false unless the client sets
`trust_env=False`.

With `HTTP_PROXY` set in the environment, a plain-http loopback request goes to the proxy. So does
every header on it, including credentials you believed stayed local.

```python
client = httpx.Client(trust_env=False)   # required for a real egress guarantee
```

`requests` has the same exposure through `session.trust_env`.

**How to apply:** When a design rests on a request staying local, set `trust_env=False` explicitly
and assert it in a test. Do not rely on the absence of a proxy variable in your own shell. Another
process, a corporate profile, or a CI runner can set one.

## `localhost` Is a Name, Not a Network Guarantee

An `/etc/hosts` entry moves `localhost` anywhere. A loopback check must:

1. Resolve the name.
2. Confirm **every** returned address is loopback.
3. Fail **closed** on a lookup error.

**Corollary — unify the predicate.** If two checks key on "local" differently, one on the hostname
string and one on the resolved address, they will disagree at exactly the moment it matters. Pick
one predicate and use it in both places.

**How to apply:** Never accept a string comparison against `"localhost"` or `"127.0.0.1"` as a
security control. Resolve, then check the addresses.
