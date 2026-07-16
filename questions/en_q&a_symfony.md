# Symfony Framework Technical Interview Q&A

## 🔹 Core Architecture & Components

### Q1: What is the Symfony Kernel and how does it handle HTTP requests?
**Answer:** The `HttpKernel` is the core of Symfony. It listens to `kernel.*` events, matches the route via the `Router`, resolves the controller via the `ControllerResolver`, executes it, and returns a `Response` object. The entire lifecycle is event-driven and managed through the `HttpKernelInterface`.
**References:** [Symfony HttpKernel Component](https://symfony.com/doc/current/components/http_kernel.html) | [Request Lifecycle](https://symfony.com/doc/current/page_creation.html)

---

### Q2: How does Symfony's component-based architecture differ from monolithic frameworks?
**Answer:** Symfony is decoupled into ~50 independent components (e.g., HttpFoundation, Routing, DependencyInjection). You can use them standalone or together. The `FrameworkBundle` glues them into a full-stack framework. This enables lightweight microservices, custom stacks, and easier testing/updates.
**References:** [Symfony Components](https://symfony.com/components) | [Full-Stack vs Micro Framework](https://symfony.com/doc/current/bundles.html)

---

## 🔹 Dependency Injection & Service Container

### Q3: How does Symfony's Service Container work, and what is autoconfiguration/autoinject?
**Answer:** The container manages object instantiation and wiring. In modern Symfony, services are auto-registered via PHP attributes (`#[AsController]`, `#[Autoconfigure]`) and directory scanning. Type-hinting in constructors triggers automatic injection. The container is compiled to optimized PHP classes for zero-runtime overhead in production.
**References:** [Service Container Documentation](https://symfony.com/doc/current/service_container.html) | [Autowiring & Autoconfigure](https://symfony.com/doc/current/service_container/autowiring.html)

---

### Q4: What are Compiler Passes and when should you use them?
**Answer:** "Compiler passes give you an opportunity to manipulate other service definitions that have been registered with the service container."
Compiler passes are classes that run during container compilation (cache warmup) to programmatically modify service definitions, process tags, or validate configurations. They execute once before the optimized container is cached. Use them for dynamic service registration, tag processing, or framework integrations.
**References:** [Compiler Passes Guide](https://symfony.com/doc/current/service_container/compiler_passes.html)

---

### Q5: What is the difference between `bind`, `alias`, and `decorator` in service configuration?
**Answer:** 
- `bind`: Injects a specific value/dependency into parameters matching a name/type across services.
- `alias`: Maps one service ID/interface to another implementation.
- `decorator`: Wraps an existing service with additional behavior while preserving the original contract (using `#[AsDecorator]` or manual decoration).
**References:** [Service Configuration](https://symfony.com/doc/current/service_container.html#creating-configuring-services-in-the-container) | [Service Decorators](https://symfony.com/doc/current/service_container/service_decoration.html)

---

## 🔹 Routing & Controllers

### Q6: How does modern Symfony handle routing with PHP attributes vs YAML/XML?
**Answer:** Since Symfony 5.4/6+, routing is primarily defined via PHP attributes (`#[Route('/path', name: '...')]`) directly on controllers or classes. This colocation improves DX, enables static analysis, and removes separate config files. YAML/XML is still supported but discouraged for new projects.
**References:** [Routing with Attributes](https://symfony.com/doc/current/routing.html#creating-routes) | [Attribute Configuration](https://symfony.com/doc/current/routing.html#routing-configuration-attributes)

---

### Q7: What is the Controller Resolver and how does it handle argument resolution?
**Answer:** The `ArgumentResolver` inspects controller method signatures, matches route parameters, resolves services via the DI container, and handles special objects like `Request`, `Session`, or `UserInterface`. Custom resolvers can be registered via the `controller.argument_value_resolver` tag.
**References:** [Argument Resolver](https://symfony.com/doc/current/controller/argument_resolver.html) | [Value Resolver Interface](https://github.com/symfony/symfony/blob/6.4/src/Symfony/Component/HttpKernel/Controller/ArgumentResolver/ArgumentValueResolverInterface.php)

---

## 🔹 Doctrine ORM & Database

### Q8: How does Symfony integrate with Doctrine, and what is the recommended approach for repositories?
**Answer:** Symfony autoconfigures Doctrine via `DoctrineBundle`. Repositories should extend `ServiceEntityRepository` (not `EntityRepository`) to leverage DI, auto-injection, and type safety. Use `QueryBuilder` for complex queries, avoid N+1 with explicit `JOIN`s or `fetch="EAGER"`, and prefer DTOs for read-only projections.
**References:** [Doctrine in Symfony](https://symfony.com/doc/current/doctrine.html) | [ServiceEntityRepository](https://symfony.com/doc/current/doctrine/repository.html)

---

### Q9: What is the difference between `EntityManager::flush()` and `persist()`, and how should transactions be managed?
**Answer:** `persist()` marks an entity for insertion; `flush()` synchronizes all pending changes to the DB in a single transaction. Use `EntityManager::transactional()` or `#[Transaction]` (Symfony 6.3+) for declarative transaction handling. Keep transactions short to avoid locks.
**References:** [EntityManager Usage](https://symfony.com/doc/current/doctrine.html#persisting-objects-to-the-database) | [Transactional Attribute](https://symfony.com/doc/current/doctrine/transactions.html)

---

## 🔹 Security & Authentication

### Q10: How does Symfony's Security Component work in v6+?
**Answer:** Symfony 6+ uses a unified `security.yaml` configuration with `authenticators` replacing the old guard system. It relies on the `Firewall` concept, `UserProvider` for identity loading, and `AuthenticatorInterface` for login logic. Password hashing is handled via `PasswordHasherInterface`.
**References:** [Security Guide](https://symfony.com/doc/current/security.html) | [Custom Authenticator](https://symfony.com/doc/current/security/custom_authenticator.html)

---

### Q11: How do you implement API authentication with JWT or Session in Symfony?
**Answer:** For SPAs/APIs, use `lexik/jwt-authentication-bundle` or native `json_login` + stateless firewalls. For session-based auth, configure `form_login` with `remember_me` and `same_site` cookies. Always set `stateless: true` for APIs and use `Security::getUser()` for access control.
**References:** [API Authentication](https://symfony.com/doc/current/security.html#stateless-authentication) | [JWT Bundle](https://github.com/lexik/LexikJWTAuthenticationBundle)

---

## 🔹 Testing & Quality

### Q12: How do you write effective functional and unit tests in Symfony?
**Answer:** Use `WebTestCase` for functional tests with `KernelBrowser` to simulate HTTP requests. Mock external services with `test.service_container` or PHPUnit mocks. Use `DoctrineTestBundle` for database resets per test. Prefer `#[KernelTestCase]` for service-level tests and avoid full container boot when possible.
**References:** [Testing Documentation](https://symfony.com/doc/current/testing.html) | [WebTestCase Guide](https://symfony.com/doc/current/testing.html#functional-tests)

---

### Q13: What is the role of `phpunit.xml.dist` and Symfony's test environment?
**Answer:** It configures the `APP_ENV=test` environment, disables caching, enables debug mode, and sets up test-specific services (e.g., in-memory DB, mailer transport `null://`). Ensures isolation, deterministic state, and faster test execution.
**References:** [Test Environment Setup](https://symfony.com/doc/current/testing.html#your-first-functional-test) | [Symfony PHPUnit Bridge](https://symfony.com/doc/current/components/phpunit_bridge.html)

---

## 🔹 Performance & Production

### Q14: How does Symfony optimize performance in production?
**Answer:** Via `APP_ENV=prod`, `APP_DEBUG=0`, container compilation, route/config caching (`cache:clear`, `cache:warmup`), OPcache, and disabling debug toolbar/logger handlers. Use `symfony/runtime` for optimized entry points and consider PHP-FPM tuning or async runtimes for high load.
**References:** [Deployment Guide](https://symfony.com/doc/current/deployment.html) | [Performance Tuning](https://symfony.com/doc/current/performance.html)

---

### Q15: How do you handle asynchronous tasks and message queues in Symfony?
**Answer:** Use `symfony/messenger` with transport adapters (Doctrine, Redis, RabbitMQ, AMQP). Define message handlers via `#[AsMessageHandler]`, configure retries, failed message handling, and monitoring. Enables decoupled, scalable background processing.
**References:** [Messenger Documentation](https://symfony.com/doc/current/messenger.html) | [Transports & Handlers](https://symfony.com/doc/current/messenger.html#transports)

---

## 📊 Quick Reference: Modern Symfony Best Practices
| Area | Best Practice | Avoid |
| :--- | :--- | :--- |
| **Routing** | PHP attributes (`#[Route]`) | Separate YAML/XML for simple apps |
| **DI** | Constructor injection + autowiring | `$container->get()` in controllers |
| **ORM** | `ServiceEntityRepository` + DTOs | `EntityManager` in controllers |
| **Security** | Authenticators + `#[IsGranted]` | Custom security checks in business logic |
| **Testing** | `WebTestCase` + `DoctrineTestBundle` | Full container boot for unit tests |
| **Config** | `services.yaml` + environment variables | Hardcoded secrets or inline YAML |

---

## 📚 Official Resources
- [Symfony 6/7 Documentation](https://symfony.com/doc/current/index.html)
- [Symfony Best Practices](https://symfony.com/doc/current/best_practices.html)
- [SymfonyCasts Tutorials](https://symfonycasts.com/)
- [Symfony GitHub Components](https://github.com/symfony/symfony/tree/6.4/src/Symfony/Component)
- [Doctrine ORM in Symfony](https://symfony.com/doc/current/doctrine.html)
- [Security Guide](https://symfony.com/doc/current/security.html)
- [Testing Guide](https://symfony.com/doc/current/testing.html)
- [Deployment Guide](https://symfony.com/doc/current/deployment.html)
