# Additional Symfony Framework Interview Q&A

## 🔹 Events, Forms & Console

### Q16: How does Symfony's Event Dispatcher work, and when should you use Subscribers vs Listeners?
**Answer:** The Event Dispatcher follows the Observer pattern. **Listeners** are registered per event via `#[AsEventListener]` or `services.yaml`. **Subscribers** implement `EventSubscriberInterface` and return an array of events → methods. Use Subscribers when one class handles multiple related events; use Listeners for simple, single-event hooks. Both are resolved by the DI container.
**References:** [Event Dispatcher Component](https://symfony.com/doc/current/components/event_dispatcher.html) | [Listeners vs Subscribers](https://symfony.com/doc/current/event_dispatcher.html#event-subscribers)

---

### Q17: How do Symfony Forms handle validation, CSRF, and data mapping?
**Answer:** Forms bind HTTP data to objects/arrays, apply `#[Assert\...]` constraints, and auto-generate CSRF tokens. `handleRequest()` merges request data, `isValid()` runs validation, and data mappers transform complex types (e.g., Choice → Entity). Always validate server-side; client-side validation is UX-only. Use `FormType` interfaces for reusability.
**References:** [Forms Documentation](https://symfony.com/doc/current/forms.html) | [CSRF Protection in Forms](https://symfony.com/doc/current/security/csrf.html#forms)

---

### Q18: What are Symfony Console Commands, and how do you handle arguments, options, and progress output?
**Answer:** Commands extend `Symfony\Component\Console\Command\Command`. Define `configure()` for arguments/options, `execute()` for logic. Use `SymfonyStyle` for formatted tables, progress bars, and interactive questions. Register via `#[AsCommand]` or DI. Ideal for cron jobs, migrations, and admin scripts.
**References:** [Console Component](https://symfony.com/doc/current/console.html) | [Advanced Input/Output](https://symfony.com/doc/current/console/input_output.html)

---

## 🔹 Cache, Serialization & HTTP

### Q19: How does Symfony's Cache Component handle tagging and granular invalidation?
**Answer:** Implements PSR-6/PSR-18. Cache tags group items logically (e.g., `product_42`). Requires tag-aware adapters (Redis, Memcached, APCu). Invalidating a tag clears all associated items without flushing the entire pool. Use `#[Cache]` attribute or `TagAwareCacheInterface` for explicit control.
**References:** [Cache Component](https://symfony.com/doc/current/cache.html) | [Cache Tags](https://symfony.com/doc/current/cache.html#cache-tags)

---

### Q20: What is the Symfony Serializer Component, and how does it differ from JMS Serializer?
**Answer:** Converts objects ↔ arrays/JSON/XML using Normalizers + Encoders. Uses `#[Groups]`, `#[SerializedName]`, `#[Ignore]` attributes. Faster, native, and tightly integrated. JMS Serializer is heavier but supports complex metadata, virtual properties, and legacy mapping. Prefer native Symfony serializer for new projects.
**References:** [Serializer Component](https://symfony.com/doc/current/components/serializer.html) | [Native vs JMS](https://symfony.com/doc/current/serializer.html#jms-serializer)

---

### Q21: How does Symfony handle HTTP caching, ESI, and reverse proxy integration?
**Answer:** Uses `HttpCache` (Symfony's built-in reverse proxy) or external (Varnish/CDN). Set cache headers via `#[Cache]` or `Response::setPublic()/setMaxAge()`. ESI (`<esi:include>`) caches page fragments independently. `Vary` headers handle user-specific content. Reverse proxies intercept requests before hitting PHP.
**References:** [HTTP Cache Guide](https://symfony.com/doc/current/http_cache.html) | [ESI Fragments](https://symfony.com/doc/current/http_cache/esi.html)

---

## 🔹 Security, Reliability & Architecture

### Q22: Explain Symfony's Rate Limiter component and how to protect APIs.
**Answer:** Provides fixed-window, sliding-window, and token-bucket algorithms. Configured in `framework.yaml` with policies per IP/route/user. Integrated into firewalls via `rate_limiter:`. Returns `429 Too Many Requests` when exceeded. Ideal for login endpoints, public APIs, and brute-force prevention.
**References:** [Rate Limiter Documentation](https://symfony.com/doc/current/rate_limiter.html) | [Firewall Integration](https://symfony.com/doc/current/security/rate_limiter.html)

---

### Q23: How does the Lock Component prevent race conditions in CLI/queue workers?
**Answer:** Provides distributed locks via Redis, PDO, or semaphore. Acquired via `LockFactory::createLock()` with TTL. Auto-releases on timeout or process death. Prevents duplicate cron execution, concurrent job processing, and resource collisions. Use `acquire()`/`release()` or `#[Lock]` attribute.
**References:** [Lock Component](https://symfony.com/doc/current/components/lock.html) | [Distributed Locking Guide](https://symfony.com/doc/current/lock.html)

---

### Q24: What is the Workflow Component and when is it useful?
**Answer:** Manages state machines for entities. Defines states, transitions, guards, and events. Enforces valid transitions, prevents illegal state changes, and visualizable via PlantUML. Useful for order processing, approval flows, ticket systems, and content moderation.
**References:** [Workflow Component](https://symfony.com/doc/current/workflow.html) | [State Machines vs Petri Nets](https://symfony.com/doc/current/components/workflow.html)

---

### Q25: How do you create a reusable Symfony Bundle and when is it necessary?
**Answer:** Bundles package framework-coupled code (controllers, forms, DI extensions, templates). Modern Symfony favors standalone Composer packages for pure PHP logic. Create bundles only when tightly integrated with Symfony features. Register via `Kernel::registerBundles()` or autoconfigure with `symfony/flex`. Follow `Bundle` naming and `Resources/` conventions.
**References:** [Bundle Best Practices](https://symfony.com/doc/current/bundles.html) | [Creating a Bundle](https://symfony.com/doc/current/bundles/best_practices.html)

---

## 📊 Quick Reference: Advanced Symfony Patterns
| Component | Primary Use | Key Feature | Modern Syntax |
| :--- | :--- | :--- | :--- |
| **Event Dispatcher** | Decoupled hooks | `#[AsEventListener]` / Subscribers | Attribute-based |
| **Serializer** | Object ↔ JSON/XML | `#[Groups]`, `#[Ignore]` | Native, fast |
| **Cache** | PSR-6/PSR-18 storage | Tag invalidation | `#[Cache]` attribute |
| **Rate Limiter** | API/Endpoint protection | Sliding window, token bucket | `framework.yaml` |
| **Lock** | Distributed mutex | Redis/PDO, auto-expire | `#[Lock]` attribute |
| **Workflow** | State machines | Guards, transitions, visualization | YAML/PHP config |
| **Console** | CLI tools | Progress bars, tables, interactive | `#[AsCommand]` |

---

## 📚 Official Resources
- [Symfony 6.4/7.x Documentation](https://symfony.com/doc/current/index.html)
- [Symfony Components Reference](https://symfony.com/components)
- [Symfony Best Practices](https://symfony.com/doc/current/best_practices.html)
- [Console Commands Guide](https://symfony.com/doc/current/console.html)
- [Cache & HTTP Cache](https://symfony.com/doc/current/cache.html) | [https://symfony.com/doc/current/http_cache.html]
- [Security: Rate Limiter & Lock](https://symfony.com/doc/current/rate_limiter.html) | [https://symfony.com/doc/current/lock.html]
- [Workflow & State Machines](https://symfony.com/doc/current/workflow.html)
- [Serializer Component](https://symfony.com/doc/current/components/serializer.html)
