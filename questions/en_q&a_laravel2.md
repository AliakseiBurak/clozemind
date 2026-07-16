# Additional Laravel Interview Questions & Answers

## 📚 Table of Contents
- [Middleware & Routing](#middleware--routing)
- [Eloquent Advanced Features](#eloquent-advanced-features)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [API & Data Transformation](#api--data-transformation)
- [Core Framework & Architecture](#core-framework--architecture)
- [📚 References](#-references)

---

## Middleware & Routing

### Q17: How does Laravel's middleware pipeline work and in what order do they execute?
**Answer:** Middleware intercepts HTTP requests before they reach the controller. Laravel uses `Illuminate\Pipeline\Pipeline` to chain them. Execution order:
1. Global middleware (`$middleware` in Kernel)
2. Route/Group middleware (`->middleware()`)
3. Controller middleware (`$this->middleware()`)
Each middleware calls `$next($request)` to pass control forward. If a middleware returns a `Response`, the pipeline short-circuits and skips remaining middleware. Order matters for security (e.g., auth before rate limiting).

---

### Q18: What is route caching and when should you use it?
**Answer:** `php artisan route:cache` compiles all routes into a single optimized PHP file, eliminating runtime route parsing. Reduces bootstrap time significantly.
**When to use:** Production deployments with static route definitions.
**Caveat:** Fails if routes use Closures or dynamic route generation. Always run `php artisan route:clear` during deployment before caching.

---

## Eloquent Advanced Features

### Q19: What is the difference between local and global scopes?
**Answer:** 
- **Local Scope:** Defined as `scopeName()` on the model. Applied explicitly: `User::active()->get();`
- **Global Scope:** Applied automatically to all queries on the model. Implemented via `Illuminate\Database\Eloquent\Scope` interface and registered in `booted()`.
**Use Cases:** Global scopes for soft deletes, multi-tenancy, or tenant filtering. Local scopes for reusable query conditions (`recent()`, `verified()`).

---

### Q20: When should you use Eloquent Observers vs Model Events?
**Answer:** 
- **Model Events:** Triggered automatically (`creating`, `saved`, `deleting`, etc.). Handled via closures in `boot()` or `static::saved()`.
- **Observers:** Group multiple event handlers into a single class. Registered via `$model->observe(Observer::class)` or auto-discovered.
**Rule:** Use observers when handling 3+ events for one model. Use events/listeners for decoupled, cross-model logic. Observers keep model code clean and testable.

---

### Q21: How do Eloquent Accessors, Mutators, and Attribute Casting work?
**Answer:** 
- **Accessors/Mutators (Legacy):** `getNameAttribute()`, `setNameAttribute()`
- **Modern Attributes (Laravel 9+):** `protected function name(): Attribute { return Attribute::make(get: fn($v) => strtoupper($v), set: fn($v) => strtolower($v)); }`
- **Casting:** `$casts = ['is_active' => 'boolean', 'metadata' => 'array', 'birthday' => 'date'];`
**Benefit:** Centralizes data transformation, ensures consistent types, and removes manual parsing from controllers.

---

## Testing & Quality Assurance

### Q22: What is the difference between Unit and Feature tests in Laravel?
**Answer:** 
- **Unit Tests:** Isolate a single class/method. No HTTP kernel, no DB. Fast. Use `TestCase` or `Pest` `test()`.
- **Feature Tests:** Simulate full HTTP requests, interact with DB, test routes/controllers. Use `$this->get()`, `$this->post()`, `assertStatus()`.
**Best Practice:** ~70% unit, ~30% feature. Mock external APIs with `Http::fake()`, queues with `Queue::fake()`, and storage with `Storage::fake()`.

---

### Q23: How do you test code that depends on external services or time?
**Answer:** 
- **HTTP Calls:** `Http::fake(['api.example.com/*' => Http::response(['data' => 'ok'], 200)]);`
- **Queues/Jobs:** `Queue::fake();`, then `Queue::assertPushed(EmailJob::class);`
- **Time/Carbon:** `Carbon::setTestNow(now());` to freeze time in tests.
- **Facades:** Use `Mockery` or Laravel's built-in `partialMock()`/`spy()` for complex service interactions.
**Tip:** Always reset fakes/mocks in `tearDown()` or use `@after` hooks.

---

## API & Data Transformation

### Q24: What are Laravel API Resources and why use them over raw arrays?
**Answer:** API Resources transform Eloquent models/collections into consistent JSON responses. They provide:
- Explicit field mapping (hides DB columns)
- Conditional attributes (`when($this->admin, ...)`)
- Pagination metadata & links
- Versioning support
- Reusability across endpoints
**Usage:** `UserResource::make($user)` or `UserResource::collection($users)`. Prevents tight coupling between schema and API contract.

---

### Q25: How does Laravel handle API versioning and backward compatibility?
**Answer:** 
- **URL Versioning:** `api/v1/users`, `api/v2/users` (routes grouped by prefix)
- **Header Versioning:** `Accept: application/vnd.myapp.v1+json` (middleware reads header, resolves routes)
- **Resource Versioning:** Create `V1/UserResource` and `V2/UserResource` to evolve responses without breaking clients.
**Best Practice:** Maintain old versions until migration window closes. Document breaking changes in API changelog. Use contract testing to validate compatibility.

---

## Core Framework & Architecture

### Q26: What are Laravel Facades and when should you avoid them?
**Answer:** Facades provide static-like syntax to underlying container-bound services (e.g., `Cache::get()`, `Log::info()`). They resolve services at runtime via `__callStatic()` and `getFacadeRoot()`.
**Avoid when:** 
- Writing highly testable code (harder to mock than injected dependencies)
- Building libraries/packages (explicit DI is preferred)
- Working in strict OOP environments
**Use when:** Quick access in views, Artisan commands, or when static syntax improves readability. Always prefer DI in controllers/services.

---

### Q27: How does Laravel's Task Scheduler work and what are common pitfalls?
**Answer:** Defined in `routes/console.php` (Laravel 11+) or `App\Console\Kernel`. Uses fluent API:
```php
Schedule::command('reports:generate')->dailyAt('02:00')->withoutOverlapping()->onOneServer();
```
Requires single cron entry: `* * * * * php /path/to/artisan schedule:run`
**Pitfalls:** 
- Missing cron entry on production servers
- Not using `onOneServer()` in multi-node deployments (causes duplicate runs)
- Long-running tasks blocking subsequent schedules
- Not logging output: `->appendOutputTo(storage_path('logs/schedule.log'))`

---

### Q28: What is the Laravel Request Lifecycle from `index.php` to response?
**Answer:**
1. `public/index.php` loads Composer autoloader & creates `Application` instance
2. HTTP Kernel boots: loads config, environment, service providers (`register()` → `boot()`)
3. Middleware pipeline processes request (auth, CSRF, rate limiting, etc.)
4. Router matches URI to controller/action or Closure
5. Controller executes, resolves dependencies via Service Container
6. Response generated (View, JSON, Redirect, etc.)
7. Termination middleware runs (`terminate()` method)
8. Response sent to client
**Octane Optimization:** Steps 1-3 are cached in memory for subsequent requests, skipping bootstrap overhead.

---

### Q29: How does Laravel handle database connections and multi-tenancy?
**Answer:** Connections are defined in `config/database.php`. Switch at runtime via:
```php
DB::connection('tenant_123')->table('users')->get();
```
For multi-tenancy:
- Use middleware to resolve tenant → set connection dynamically
- Or use packages like `stancl/tenancy` for automatic routing, DB switching, and cache isolation
- Ensure migrations run per-tenant or use shared DB with `tenant_id` column (row-level tenancy)
**Best Practice:** Never hardcode connection names; resolve them from request context or session.

---

### Q30: What are Blade Components and how do they differ from traditional `@include`?
**Answer:** Blade Components are reusable, object-oriented UI building blocks with dedicated classes and props.
- **Class-based:** `php artisan make:component Alert` → `app/View/Components/Alert.php` + `resources/views/components/alert.blade.php`
- **Anonymous:** Directly in `resources/views/components/`
- **Features:** `$props`, `{{ $slot }}`, conditional rendering, data encapsulation, versioning
- **vs `@include`:** `@include` is simple templating; components support logic, validation, and encapsulated state. Introduced in Laravel 7+, refined in 8/9/10+.

---

## 📚 References

1. [Laravel Middleware](https://laravel.com/docs/11.x/middleware)
2. [Route Caching](https://laravel.com/docs/11.x/deployment#optimizing-route-loading)
3. [Eloquent Scopes](https://laravel.com/docs/11.x/eloquent#query-scopes)
4. [Eloquent Observers](https://laravel.com/docs/11.x/eloquent#observers)
5. [Eloquent Casting & Attributes](https://laravel.com/docs/11.x/eloquent-mutators)
6. [Laravel Testing](https://laravel.com/docs/11.x/testing)
7. [HTTP Client Faking](https://laravel.com/docs/11.x/http-client#faking)
8. [API Resources](https://laravel.com/docs/11.x/eloquent-resources)
9. [Task Scheduling](https://laravel.com/docs/11.x/scheduling)
10. [Facades Documentation](https://laravel.com/docs/11.x/facades)
11. [Database Connections](https://laravel.com/docs/11.x/database#using-multiple-database-connections)
12. [Blade Components](https://laravel.com/docs/11.x/blade#components)
