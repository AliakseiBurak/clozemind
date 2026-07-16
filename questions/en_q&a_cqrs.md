# CQRS Interview Questions: Command Return Semantics & API Design

## 📚 Table of Contents
- [Command Return Semantics](#command-return-semantics)
- [Strict vs Relaxed Returns](#strict-vs-relaxed-returns)
- [Practical API Design](#practical-api-design)
- [📊 Quick Reference](#-quick-reference)
- [💡 Interview Tips](#-interview-tips)
- [References](#references)
- [✅ Self-Check](#-self-check)

---

## Command Return Semantics

### Q1: What should a CQRS command return, and why does it differ from queries?
**Answer:** Commands modify state and should return minimal, actionable data: a command ID, status, or validation errors. Queries read state and return full data projections. Commands avoid returning domain state to prevent coupling the write model to read expectations and to keep execution fast.

**Example:**
```http
POST /commands/place-order
Response: 202 Accepted
{ "commandId": "cmd_8f3a", "status": "accepted" }
```
No order details or aggregates are returned.

**Source:** [Microsoft CQRS Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)

---

### Q2: What are the three common command return patterns in CQRS?
**Answer:**
1. **Synchronous Result:** Returns success/failure + created IDs immediately.
2. **Asynchronous Acknowledgment:** Returns `202 Accepted` + command ID; processing happens in background.
3. **Event-Driven Notification:** Returns acknowledgment; completion/failure is signaled via domain events, webhooks, or message brokers.

**Example:** E-commerce checkout uses async ack + webhook for payment confirmation; user profile update uses sync result for immediate UI feedback.

**Source:** [Greg Young: CQRS Documents](https://cqrs.nu/)

---

### Q3: Why shouldn't commands return updated aggregate state?
**Answer:** Returning state couples the write model to read contracts, breaks CQRS separation, and forces the command handler to perform read-side projections synchronously. This increases latency, complicates caching, and violates the single-responsibility principle. Clients should fetch updated state via queries after command completion.

**Example Risk:** `POST /users/update-email` returns full user profile. If the read model is eventually consistent, the returned data may be stale or mismatched, confusing clients.

**Source:** [Martin Fowler: CQRS](https://martinfowler.com/bliki/CQRS.html)

---

## Strict vs Relaxed Returns

### Q4: Explain strict vs relaxed command return semantics.
**Answer:**
- **Strict (Synchronous):** Client blocks until command is fully validated, executed, and persisted. Returns immediate result or error. Guarantees strong consistency but limits throughput and scales poorly under load.
- **Relaxed (Asynchronous):** Client receives immediate acknowledgment. Command is queued and processed later. Returns `202 Accepted` + tracking ID. Enables high scalability, retry tolerance, and eventual consistency, but requires client-side state tracking.

**Example:** Banking transfer uses strict semantics (must confirm balance deduction instantly). Social media post uses relaxed semantics (accepted immediately, fans out later).

**Source:** [Udi Dahan: CQRS, Task-Based UI](https://udidahan.com/)

---

### Q5: How do you handle timeouts and retries with relaxed semantics?
**Answer:**
- Use **idempotency keys** to prevent duplicate processing on retries.
- Return `202 Accepted` immediately; never retry on `2xx`.
- Client polls status endpoint or subscribes to events.
- Implement exponential backoff for polling/webhook delivery.
- Log command lifecycle for auditability.

**Example Flow:**
```http
POST /commands/cancel-subscription
Headers: Idempotency-Key: req_99x
Response: 202 Accepted
{ "commandId": "cmd_77b", "statusUrl": "/commands/cmd_77b/status" }

GET /commands/cmd_77b/status
Response: 200 OK
{ "state": "completed", "completedAt": "2024-06-10T14:32:00Z" }
```

**Source:** [RFC 9110: HTTP Status Codes](https://www.rfc-editor.org/rfc/rfc9110.html)

---

### Q6: When should you choose strict over relaxed semantics?
**Answer:** Choose strict when:
- Business rules require immediate consistency (e.g., inventory deduction, payment authorization)
- Client UX depends on instant feedback (e.g., form validation, blocking UI)
- Command execution is fast (<100ms) and stateless
- Retry complexity outweighs async benefits

Choose relaxed when:
- Commands trigger long-running workflows or external integrations
- System must handle traffic spikes or batch processing
- Eventual consistency is acceptable
- Decoupling client/server latency is critical

**Source:** [AWS Well-Architected: Asynchronous Integration](https://docs.aws.amazon.com/wellarchitected/latest/framework/async-integration.html)

---

## Practical API Design

### Q7: How do you structure REST endpoints for CQRS commands?
**Answer:**
- Use `POST /commands` or `POST /aggregates/{id}/commands`
- Include `Idempotency-Key` header
- Return `202 Accepted` with `Location` header pointing to status resource
- Use `400 Bad Request` for validation, `409 Conflict` for business rule violations, `429 Too Many Requests` for rate limits
- Never use `GET`, `PUT`, or `DELETE` for commands

**Example:**
```http
POST /orders/cmd_8f3a/ship
Content-Type: application/json
Idempotency-Key: ship_req_001

{
  "trackingNumber": "1Z999AA10123456784",
  "carrier": "UPS"
}
```

**Source:** [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)

---

### Q8: How do you expose command status and results to clients?
**Answer:**
- **Polling:** `GET /commands/{id}/status` returns state machine (`accepted`, `processing`, `completed`, `failed`)
- **Webhooks:** Client registers callback URL; server POSTs result when done
- **SSE/WebSockets:** Real-time streaming for UI dashboards
- **Message Queue:** Internal services consume completion events

**Best Practice:** Combine polling fallback with webhook/SSE for real-time apps. Always include `retry-after` headers and error details in failed states.

**Source:** [Webhook Best Practices](https://webhooks.fyi/)

---

### Q9: How do you handle command validation errors in CQRS APIs?
**Answer:**
- **Sync validation** (schema, auth, business rules) → `400 Bad Request` with structured error body
- **Async validation** (external deps, eventual checks) → `202 Accepted` → later `failed` status with error details
- Use RFC 7807 `application/problem+json` for consistent error formatting
- Never expose internal stack traces or DB errors

**Example Error Response:**
```json
{
  "type": "https://api.example.com/errors/insufficient-funds",
  "title": "Command Rejected",
  "status": 400,
  "detail": "Account balance is insufficient to complete transfer",
  "commandId": "cmd_8f3a"
}
```

**Source:** [RFC 7807: Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)

---

### Q10: How do you ensure idempotency in CQRS command APIs?
**Answer:**
- Require `Idempotency-Key` header (UUID or client-generated)
- Store key + result in cache/DB with TTL
- On duplicate key, return cached response + `200 OK` or `202 Accepted`
- Invalidate key only after command completes or expires
- Log key usage for audit and debugging

**Example Implementation:**
```python
key = request.headers["Idempotency-Key"]
if cache.exists(key):
    return cache.get(key)
result = process_command(request)
cache.set(key, result, ttl=86400)
return result
```

**Source:** [Stripe API: Idempotent Requests](https://stripe.com/docs/api/idempotent_requests)

---

##  Quick Reference

| Pattern | Return Type | Latency | Consistency | Client Complexity | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Strict Sync** | Result/Error immediately | Low | Strong | Low | Payments, auth, validation |
| **Relaxed Async** | `202` + command ID | Very Low | Eventual | Medium-High | Workflows, integrations, scaling |
| **Polling** | `GET /status` | Variable | Eventual | Medium | Web apps, background jobs |
| **Webhooks/SSE** | Push notification | Real-time | Eventual | High | Dashboards, real-time UI |
| **Idempotent Command** | Cached result on retry | Low-Medium | Varies | Low | Network retries, mobile clients |

---

## 💡 Interview Tips

- **Clarify consistency requirements first:** Ask if the business tolerates eventual consistency or demands strong guarantees.
- **Emphasize separation of concerns:** "Commands don't return state; queries do. Mixing them breaks CQRS."
- **Discuss failure modes:** Explain how you handle timeouts, partial failures, and duplicate submissions.
- **Reference real patterns:** Mention idempotency keys, RFC 7807 errors, and status polling to show production experience.
- **Acknowledge trade-offs:** "Async scales better but shifts complexity to the client. We chose relaxed semantics because our SLA allows 500ms eventual consistency."

---

## References

1. [Microsoft Architecture Center: CQRS Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)
2. [Martin Fowler: CQRS](https://martinfowler.com/bliki/CQRS.html)
3. [Greg Young: CQRS Documents](https://cqrs.nu/)
4. [RFC 7807: Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)
5. [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
6. [Udi Dahan: CQRS, Task-Based UI, and SOA](https://udidahan.com/)
7. [Stripe API: Idempotent Requests](https://stripe.com/docs/api/idempotent_requests)
8. [AWS Well-Architected Framework: Asynchronous Integration](https://docs.aws.amazon.com/wellarchitected/latest/framework/async-integration.html)
9. [Webhooks.fyi: Best Practices](https://webhooks.fyi/)
10. [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines)

---

## ✅ Self-Check

- [ ] Can I explain why commands shouldn't return aggregate state?
- [ ] Do I know the difference between strict and relaxed return semantics?
- [ ] Can I design a REST endpoint for async commands with idempotency?
- [ ] Do I understand how to handle validation errors synchronously vs asynchronously?
- [ ] Can I choose between polling, webhooks, and SSE based on client needs?
- [ ] Do I know how to implement and explain idempotency keys in practice?

*Practice explaining these concepts aloud. Use the quick reference table to memorize trade-offs.*
