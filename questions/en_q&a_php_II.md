# Senior PHP Developer & Software Engineer Interview Questions

## 🔹 PHP Internals & Runtime

### Q1: Describe the PHP request lifecycle from entry to response. Where do bottlenecks typically occur?
**Answer:** `index.php` → Composer autoload → Framework bootstrap → Service container resolution → Middleware pipeline → Routing → Controller execution → Response generation → Termination middleware. Bottlenecks usually stem from autoloader overhead, large object graphs, unoptimized DB queries, external API latency, or missing OPcache preloading.
**References:** [PHP Manual: Execution & Lifecycle](https://www.php.net/manual/en/internals.php) | [Laravel Request Lifecycle](https://laravel.com/docs/11.x/lifecycle) | [Symfony HTTP Kernel](https://symfony.com/doc/current/components/http_kernel.html)

---

### Q2: How does PHP manage memory? Explain `zval`, reference counting, and garbage collection.
**Answer:** PHP stores variables in `zval` structures with reference counts. When count reaches `0`, memory is freed immediately. Cyclic references trigger the cycle collector (mark-and-sweep). PHP 7.4+ improved GC performance by deferring cycle collection and using root buffers to minimize pauses.
**References:** [PHP Manual: Garbage Collection](https://www.php.net/manual/en/features.gc.php) | [Nikita Popov: PHP Memory Management](https://nikic.github.io/2015/05/05/Internal-value-representation-in-PHP-7-part-1.html)

---

### Q3: What is the role of OPcache and JIT? When does JIT provide measurable benefits?
**Answer:** OPcache caches compiled PHP bytecode in shared memory, eliminating repeated parsing/compilation. JIT translates hot execution paths to native machine code. JIT shines in CPU-bound CLI tasks (math, image processing, heavy loops) but offers minimal gains for I/O-bound web requests.
**References:** [PHP.net: OPcache](https://www.php.net/manual/en/book.opcache.php) | [PHP 8 JIT RFC](https://wiki.php.net/rfc/jit) | [Blackfire: OPcache Tuning](https://blackfire.io/docs/php/opcache)

---

## 🔹 Modern PHP (8.0–8.4+)

### Q4: How do readonly classes, typed properties, and enums improve code quality?
**Answer:** Readonly classes enforce immutability at the object level, preventing accidental state mutation. Typed properties catch type errors at runtime/parse time. Backed enums replace magic strings, provide type-safe mappings, and enable exhaustive `match` expressions.
**References:** [PHP 8.1 Readonly Properties](https://www.php.net/manual/en/language.oop5.properties.php#language.oop5.properties.readonly) | [PHP 8.1 Enums RFC](https://wiki.php.net/rfc/enumerations) | [PHP 8.2 Readonly Classes](https://wiki.php.net/rfc/readonly_classes)

---

### Q5: When should you prefer `match` over `switch`, and what are the guarantees?
**Answer:** Use `match` for strict value comparison (`===`), returning values, and enforcing exhaustiveness. It prevents accidental fall-through, supports multiple comma-separated values, and throws `UnhandledMatchError` if no arm matches.
**References:** [PHP 8.0 match Expression RFC](https://wiki.php.net/rfc/match_expression_v2) | [PHP Manual: match](https://www.php.net/manual/en/control-structures.match.php)

---

### Q6: How do PHP Attributes replace traditional DocBlocks? What are the limitations?
**Answer:** Attributes (`#[...]`) are first-class, parse-time metadata attached to classes/methods/properties. They enable static analysis, auto-wiring, and declarative configuration without string parsing. Limitations: no runtime evaluation context, limited expression syntax, and require reflection to access.
**References:** [PHP Manual: Attributes](https://www.php.net/manual/en/language.attributes.overview.php) | [PHP 8.0 Attributes RFC](https://wiki.php.net/rfc/attributes_v2)

---

## 🔹 Architecture & Design Patterns

### Q7: How do you structure a large PHP codebase to avoid framework coupling?
**Answer:** Apply Hexagonal/Clean Architecture: domain layer (pure PHP entities/value objects) → application layer (use cases/interfaces) → infrastructure layer (framework, DB, APIs). Wire boundaries via DI container. Keep framework details at the edges; business logic remains framework-agnostic.
**References:** [Clean Architecture Overview](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) | [Symfony: Decoupling Framework](https://symfony.com/doc/current/best_practices.html#decouple-your-application)

---

### Q8: When is CQRS or Event Sourcing justified in PHP? What are the trade-offs?
**Answer:** Justified when read/write workloads diverge heavily, audit/compliance requires immutable history, or complex domain workflows need replayability. Trade-offs: eventual consistency, debugging complexity, storage overhead, and steeper onboarding. Avoid for simple CRUD.
**References:** [Microsoft CQRS Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs) | [Event Sourcing in PHP](https://eventstore.com/blog/event-sourcing-in-php/) | [CQRS Journey](https://cqrs.nu/)

### Q9: How do you enforce Dependency Inversion without relying on magic container resolution?
**Answer:** Define interfaces in inner layers, implement in outer layers. Wire dependencies explicitly in composition root (e.g., `bootstrap/app.php` or `Kernel`). Use constructor injection, avoid `make()`/`app()` in business logic, and prefer explicit factories or builders for complex graphs.
**References:** [SOLID: Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle) | [Laravel Service Container](https://laravel.com/docs/11.x/container)

---

## 🔹 Performance & Scalability

### Q10: How do you profile a slow PHP request in production?
**Answer:** Use APM tools (Blackfire, Tideways, New Relic) to capture flame graphs. Prioritize: DB query plans (`EXPLAIN`), cache hit ratios, external API latency, and memory peaks. Validate with `EXPLAIN ANALYZE` and enable slow query logs.
**References:** [Blackfire.io Profiling](https://blackfire.io/docs/introduction) | [Xdebug Profiler](https://xdebug.org/docs/profiler) | [MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.0/en/explain.html)

---

### Q11: How does PHP's request-per-process model impact scaling? How do you compensate?
**Answer:** Each request bootstraps independently, increasing CPU/memory overhead under load. Compensate with OPcache preloading, stateless design, Redis session/cache, connection poolers (PgBouncer/ProxySQL), and async queues for heavy tasks.
**References:** [12 Factor App: Processes](https://12factor.net/processes) | [PHP-FPM Tuning Guide](https://www.php.net/manual/en/install.fpm.configuration.php) | [Nginx + PHP-FPM Best Practices](https://www.nginx.com/resources/wiki/start/topics/examples/phpfcgi/)

---

### Q12: Strategies to avoid N+1, connection exhaustion, and transaction bloat?
**Answer:** Use eager loading/constrained queries, paginate with cursors, pool DB connections, batch inserts/updates, keep transactions short, and move heavy work to queues. Monitor query counts per request in CI/dev.
**References:** [Laravel Eager Loading](https://laravel.com/docs/11.x/eloquent-relationships#eager-loading) | [Doctrine Query Optimization](https://www.doctrine-project.org/projects/doctrine-orm/en/stable/tutorials/optimizing.html) | [Connection Pooling Best Practices](https://www.cockroachlabs.com/blog/connection-pooling/)

---

## 🔹 Security & Resilience

### Q13: How do you prevent PHP object injection and secure deserialization?
**Answer:** Never `unserialize()` untrusted input. Use JSON with strict schema validation. If serialization is mandatory, use `allowed_classes: false` or explicit whitelists. Audit `__wakeup`, `__destruct`, and `__toString` for side effects.
**References:** [OWASP: PHP Deserialization](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html) | [PHP Manual: unserialize](https://www.php.net/manual/en/function.unserialize.php)

---

### Q14: Best practices for secure session management and CSRF in PHP SPAs/APIs?
**Answer:** Use `httponly`, `secure`, `samesite=strict/lax` cookies. Rotate session IDs post-login. For APIs, use short-lived JWTs + refresh token rotation + CSRF tokens for stateful flows. Never store tokens in `localStorage`.
**References:** [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) | [PHP Session Security](https://www.php.net/manual/en/security.php) | [Sanctum SPA Auth](https://laravel.com/docs/11.x/sanctum#spa-authentication)

---

### Q15: How do you secure PHP apps against supply-chain and path-traversal attacks?
**Answer:** Pin dependencies via `composer.lock`, use `composer audit`, restrict `open_basedir`, validate/sanitize file paths with `realpath()`, reject `../` sequences, and store uploads outside web root with randomized names.
**References:** [Composer Security Audit](https://getcomposer.org/doc/03-cli.md#audit) | [OWASP Path Traversal](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) | [PHP open_basedir](https://www.php.net/manual/en/ini.core.php#ini.open-basedir)

---

## 🔹 Testing & Quality Engineering

### Q16: How do you structure a test pyramid for PHP? When prefer integration over unit tests?
**Answer:** ~70% unit (fast, isolated logic), ~20% integration (DB, queues, APIs), ~10% E2E. Prefer integration when testing framework-heavy code, repositories, or complex workflows where mocking hides real behavior.
**References:** [Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) | [PHPUnit Best Practices](https://phpunit.de/manual/current/en/best-practices.html)

---

### Q17: How do you ensure test determinism with time, randomness, and external services?
**Answer:** Freeze time with `Carbon::setTestNow()`, seed randomness, mock HTTP via `Http::fake()`/GuzzleMockHandler, and use in-memory SQLite or test containers for DB. Reset state in `tearDown()` or transaction rollbacks.
**References:** [Laravel Testing Fakes](https://laravel.com/docs/11.x/mocking) | [PHPUnit Test Isolation](https://phpunit.de/manual/current/en/fixtures.html) | [Testcontainers](https://testcontainers.com/)

---

### Q18: Approach to static analysis (PHPStan/Psalm) and CI quality gates?
**Answer:** Enforce level 8+ PHPStan or Psalm with strict types. Run in CI as blocking step. Ignore only with documented `@phpstan-ignore` comments. Combine with Rector for automated refactoring and CS-Fixer for style consistency.
**References:** [PHPStan Configuration](https://phpstan.org/user-guide/getting-started) | [Psalm Strictness](https://psalm.dev/docs/running_psalm/configuration/) | [Rector Documentation](https://getrector.org/documentation)

---

## 🔹 System Design & Engineering Practices

### Q19: How would you design a PHP API to handle 10k+ concurrent requests with low p95 latency?
**Answer:** Stateless PHP-FPM/Swoole workers behind Nginx/Envoy, Redis caching for hot paths, read replicas for queries, async queues for writes, OPcache preloading, connection poolers, and horizontal auto-scaling. Monitor with distributed tracing.
**References:** [AWS Well-Architected: High Concurrency](https://docs.aws.amazon.com/wellarchitected/latest/framework/operational-excellence.html) | [Swoole Async PHP](https://www.swoole.co.uk/) | [Nginx Load Balancing](https://nginx.org/en/docs/http/load_balancing.html)

---

### Q20: Strategy for idempotency, retries, and dead-letter handling in PHP services?
**Answer:** Accept `Idempotency-Key` headers, cache key→response with TTL, retry with exponential backoff + jitter, mark permanent failures to DLQ, and monitor retry metrics. Ensure consumers are idempotent by design.
**References:** [Stripe Idempotency](https://stripe.com/docs/api/idempotent_requests) | [AWS Retry Strategies](https://docs.aws.amazon.com/wellarchitected/latest/framework/resiliency.html) | [RabbitMQ DLX](https://www.rabbitmq.com/dlx.html)

---

### Q21: Zero-downtime deployments & safe DB migrations in PHP?
**Answer:** Use blue/green or canary releases, expand/contract migration pattern (add column → dual-write → switch reads → drop old), run migrations in CI with `--force`, and keep them backward-compatible. Feature flags decouple deploy from release.
**References:** [Expand/Contract Pattern](https://microservices.io/patterns/data/expansion-contract.html) | [Laravel Deployment](https://laravel.com/docs/11.x/deployment) | [Feature Flags Guide](https://launchdarkly.com/)
