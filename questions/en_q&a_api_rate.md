# API Rate Limiting Interview Questions: Status Codes, Headers, Retry Behavior

## 📚 Table of Contents
- [Status Codes & Standard Headers](#status-codes--standard-headers)
- [Client Retry Behavior](#client-retry-behavior)
- [Server-Side Implementation](#server-side-implementation)
- [📊 Quick Reference](#-quick-reference)
- [ Interview Tips](#-interview-tips)
- [References](#references)
- [✅ Self-Check](#-self-check)

---

## Status Codes & Standard Headers

### Q1: Which HTTP status code indicates rate limiting, and why not `503`?
**Answer:** `429 Too Many Requests` (RFC 6585) is the standard for client-specific throttling. `503 Service Unavailable` implies server-wide failure or maintenance. Use `429` for per-client/API-key limits; reserve `503` for global circuit-breaking or overload protection.

**Example:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1718035200
```

**Source:** [RFC 6585: Additional HTTP Status Codes](https://datatracker.ietf.org/doc/html/rfc6585)

---

### Q2: What are the standard rate limit response headers?
**Answer:** 
- `X-RateLimit-Limit`: Maximum requests allowed in the current window
- `X-RateLimit-Remaining`: Requests left before hitting the limit
- `X-RateLimit-Reset`: Unix timestamp or seconds until the window resets
- `Retry-After`: Seconds or HTTP-date the client must wait before retrying

**Note:** Headers are conventionally prefixed with `X-`, but modern APIs increasingly use standard `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (IETF draft).

**Source:** [IETF HTTP RateLimit Header Fields Draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)

---

### Q3: How should a client handle the `Retry-After` header?
**Answer:** 
- Parse the value (integer seconds or HTTP-date)
- Pause all requests to that endpoint until the deadline
- Do not retry early; respect the server's explicit backoff signal
- Log the event for monitoring and quota planning

**Example:**
```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
    return make_request()
```

**Source:** [RFC 7231: Hypertext Transfer Protocol (HTTP/1.1): Semantics](https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.3)

---

## Client Retry Behavior

### Q4: What is the recommended retry strategy for rate-limited APIs?
**Answer:** Exponential backoff with jitter. Base delay doubles per attempt, capped at a maximum, plus random jitter to prevent thundering herd. Always respect `Retry-After` if present.

**Formula:** `delay = min(max_delay, base_delay * 2^attempt + uniform(0, jitter))`

**Example:** 
- Attempt 1: 1s + jitter
- Attempt 2: 2s + jitter
- Attempt 3: 4s + jitter
- Attempt 4: 8s + jitter (capped)

**Source:** [AWS Architecture Blog: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)

---

### Q5: Why is jitter critical in distributed retry logic?
**Answer:** Without jitter, synchronized clients retry simultaneously after backoff, causing renewed traffic spikes (thundering herd). Jitter randomizes retry timing, smoothing load and improving system stability.

**Example Risk:** 10,000 mobile apps hit a 429, all wait exactly 30s, then flood the API at T+30s, triggering another 429 wave. Jitter spreads retries over 30–45s.

**Source:** [Stripe API: Handling Rate Limits](https://stripe.com/docs/rate-limits)

---

### Q6: How do you safely retry non-idempotent requests?
**Answer:** 
- Require `Idempotency-Key` header (client-generated UUID)
- Server caches key → result mapping for TTL (e.g., 24h)
- On duplicate key, return cached response without re-executing
- Never retry `POST`/`PATCH` without idempotency keys

**Example:**
```http
POST /payments
Idempotency-Key: pay_9f8a7b6c
{ "amount": 5000, "currency": "USD" }
```

**Source:** [RFC 9110: HTTP Semantics (Idempotency)](https://www.rfc-editor.org/rfc/rfc9110.html#name-idempotent-methods)

---

## Server-Side Implementation

### Q7: Compare token bucket vs sliding window rate limiting algorithms.
**Answer:** 
- **Token Bucket:** Fixed capacity, refills at constant rate. Allows bursts up to bucket size. Good for traffic shaping. Simple to implement.
- **Sliding Window:** Tracks exact request count in a moving time frame. Prevents boundary bursts (e.g., 100 reqs at 0:59 + 100 at 1:01). More accurate, higher memory/CPU cost.
- **Sliding Log:** Stores timestamp of each request. Most precise, heaviest storage.

**Recommendation:** Token bucket for public APIs; sliding window for strict compliance/billing.

**Source:** [Cloudflare: Rate Limiting Algorithms](https://www.cloudflare.com/learning/ddos/rate-limiting/)

---

### Q8: Where should rate limiting be enforced in a distributed system?
**Answer:** 
- **Edge/CDN:** DDoS mitigation, IP-based global limits
- **API Gateway:** Per-client, per-key, quota management, routing
- **Service Mesh:** Inter-service call limits, circuit breaking
- **Application Layer:** Business-specific limits (e.g., export jobs, webhooks)

**Best Practice:** Multi-layer defense. Gateway handles coarse limits; app layer enforces fine-grained, domain-specific rules.

**Source:** [NGINX: Rate Limiting](https://docs.nginx.com/nginx/admin-guide/security-controls/controlling-access-proxied-http/)

---

### Q9: How do you handle rate limiting state in a clustered environment?
**Answer:** 
- Use distributed counters (Redis, Memcached, etcd)
- Atomic increment with TTL (`INCR` + `EXPIRE` in Redis)
- Sliding window: Redis sorted sets (`ZADD` + `ZREMRANGEBYSCORE` + `ZCARD`)
- Ensure clock synchronization or use server-time windows to avoid drift

**Example (Redis Sliding Window):**
```redis
MULTI
ZREMRANGEBYSCORE rate:user:123 0 <current_time - 60>
ZADD rate:user:123 <current_time> <request_id>
ZCARD rate:user:123
EXPIRE rate:user:123 60
EXEC
```

**Source:** [Redis Docs: Rate Limiting Patterns](https://redis.io/docs/manual/patterns/rate-limiting/)

---

## 📊 Quick Reference

| Component | Standard | Purpose | Client Action |
| :--- | :--- | :--- | :--- |
| `429 Too Many Requests` | RFC 6585 | Client exceeded quota | Backoff, check headers |
| `Retry-After` | RFC 7231 | Explicit wait time | Pause until deadline |
| `X-RateLimit-Limit` | De facto | Max requests/window | Track quota usage |
| `X-RateLimit-Remaining` | De facto | Requests left | Trigger proactive slowdown |
| `X-RateLimit-Reset` | De facto | Window reset time | Align polling/caching |
| `Idempotency-Key` | Industry std | Safe retry guarantee | Generate UUID per logical action |

---

## 💡 Interview Tips

- **Clarify scope:** Ask if they mean public API, internal microservices, or mobile SDK. Limits and headers differ.
- **Emphasize observability:** "We expose rate limit metrics (429 counts, quota utilization) to Grafana and alert at 80% threshold."
- **Discuss trade-offs:** "Sliding window is accurate but expensive; we use token bucket at the gateway and sliding log only for billing-critical endpoints."
- **Mention real-world patterns:** Reference Stripe, GitHub, or AWS retry strategies to show production experience.
- **Warn against common mistakes:** "Never retry without idempotency keys. Never ignore `Retry-After`. Don't hardcode backoff intervals."

---

## References

1. [RFC 6585: Additional HTTP Status Codes](https://datatracker.ietf.org/doc/html/rfc6585)
2. [RFC 7231: HTTP/1.1 Semantics and Content](https://datatracker.ietf.org/doc/html/rfc7231)
3. [IETF Draft: HTTP RateLimit Header Fields](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers)
4. [Stripe API: Rate Limits](https://stripe.com/docs/rate-limits)
5. [GitHub REST API: Rate Limiting](https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api)
6. [AWS: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
7. [Redis: Rate Limiting Patterns](https://redis.io/docs/manual/patterns/rate-limiting/)
8. [Cloudflare: Rate Limiting Algorithms](https://www.cloudflare.com/learning/ddos/rate-limiting/)
9. [NGINX: Limiting Access](https://docs.nginx.com/nginx/admin-guide/security-controls/controlling-access-proxied-http/)

---

## ✅ Self-Check

- [ ] Can I explain when to use `429` vs `503`?
- [ ] Do I know how to parse and respect `Retry-After`?
- [ ] Can I implement exponential backoff with jitter in code?
- [ ] Do I understand token bucket vs sliding window trade-offs?
- [ ] Can I design idempotent retries for `POST` endpoints?
- [ ] Do I know how to store distributed rate counters in Redis?

*Review these aloud. Simulate explaining to a frontend/mobile developer how to handle 429s in their SDK.*
