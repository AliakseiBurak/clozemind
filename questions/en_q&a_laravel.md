# Laravel Interview Questions & Answers

## 📚 Table of Contents
- [Eloquent & Performance](#eloquent--performance)
- [Security & Authentication](#security--authentication)
- [Validation & Forms](#validation--forms)
- [Advanced Laravel & Performance](#advanced-laravel--performance)
- [Core Architecture & Other Topics](#core-architecture--other-topics)
- [📚 References](#-references)

---

## Eloquent & Performance

### Q1: What is the N+1 query problem and how do you prevent it in Laravel?
**Answer:** The N+1 problem occurs when an application executes 1 query to fetch parent records, then N additional queries to fetch related child records (one per parent). This causes excessive database round-trips and degrades performance.

**Prevention in Laravel:**
- **Eager Loading:** `User::with('posts')->get();` (runs 2 queries total)
- **Lazy Eager Loading:** `$users->load('posts');` (applies after initial fetch)
- **Constrained Eager Loading:** `with(['posts' => fn($q) => $q->where('status', 'active')])`
- **Development Guard:** `Model::preventLazyLoading(!app()->isProduction());` (throws exception on lazy loads in dev)
- **Monitoring:** Use Laravel Debugbar or Telescope to spot N+1 in query logs.

---

### Q2: Explain polymorphic relations in Laravel. When should you use them?
**Answer:** Polymorphic relations allow a model to belong to multiple other models using a single association. Laravel stores `morphable_type` (class name) and `morphable_id` (foreign key) columns.

**Example:**
```php
class Comment extends Model {
    public function commentable() {
        return $this->morphTo();
    }
}

class Post extends Model {
    public function comments() {
        return $this->morphMany(Comment::class, 'commentable');
    }
}
```
**When to use:** Shared functionality across unrelated models (comments, tags, likes, attachments, audit logs).
**Trade-offs:** Highly flexible but prevents traditional foreign key constraints at the database level. Query complexity increases slightly with large datasets.

---

### Q3: What is Route Model Binding and how does it work?
**Answer:** Laravel automatically resolves Eloquent models from route parameters, eliminating manual `findOrFail()` calls.

- **Implicit Binding:** `Route::get('/users/{user}', fn(User $user) => ...)` → Laravel fetches by primary key automatically.
- **Explicit Binding:** Defined in `RouteServiceProvider::boot()`: `Route::model('user', App\Models\User::class);`
- **Custom Resolution:** `Route::bind('slug', fn($value) => Post::where('slug', $value)->firstOrFail());`

**Tip:** Use `firstOrFail()` implicitly; Laravel returns 404 if not found, keeping controllers clean.

---

## Security & Authentication

### Q4: What is mass assignment and how does Laravel protect against it?
**Answer:** Mass assignment occurs when user input is directly passed to `Model::create()` or `Model::update()`, potentially allowing attackers to modify sensitive fields (e.g., `is_admin`, `role_id`, `password`).

**Protection:**
- **Whitelist:** `$fillable = ['name', 'email'];` (recommended)
- **Blacklist:** `$guarded = ['id', 'is_admin'];`
- **Safe Input Handling:** Always use `$request->validated()` or `$request->only()` before mass assignment.

**Reference:** [Laravel Docs: Mass Assignment](https://laravel.com/docs/11.x/eloquent#mass-assignment)

---

### How should you update a user's email attribute and ensure the changes are saved to the database using Eloquent in Laravel?
**Answer:** Retrieve the model, assign the new value, and call `save()`. Alternative (mass assignment): `$user->update(['email' => 'new@example.com']);`. Both methods persist the change to the database. `save()` is preferred when modifying individual attributes, as it triggers Eloquent lifecycle events (saving, saved) and respects `$fillable`/`$guarded` rules.

---

### Q5: How does Laravel handle CSRF protection and when should you disable it?
**Answer:** Laravel automatically generates a CSRF token per session. Web forms use `@csrf`, and JS/AJAX requests must include `X-CSRF-TOKEN` or read the `XSRF-TOKEN` cookie. The `\App\Http\Middleware\VerifyCsrfToken` middleware validates all state-changing requests.

**Disable only for:** External webhooks, third-party API callbacks, or stateless API routes (Laravel's `api` middleware group excludes CSRF by default).

---

### Q6: What is Laravel Sanctum and when should you use it over Passport?
**Answer:** Sanctum is a lightweight authentication package for SPAs, mobile apps, and simple APIs.

- **SPA Auth:** Uses session cookies + CSRF protection (stateful, no JWT).
- **API Token Auth:** Issues plain tokens for mobile/third-party clients (stateless, stored in DB).
- **Choose Sanctum when:** You need simple, secure auth without OAuth2 complexity.
- **Choose Passport when:** Full OAuth2 server is required (client credentials, authorization codes, scopes, third-party integrations).

---

### Q7: What are Policies and how do they differ from Gates?
**Answer:** Both handle authorization but at different levels.

- **Gates:** Closure-based, model-agnostic checks. Best for simple, global permissions.
  `Gate::define('manage-billing', fn(User $user) => $user->isSubscribed());`
- **Policies:** Class-based, organized around a specific model. Best for CRUD operations.
  `php artisan make:policy PostPolicy --model=Post`
- **Usage:** `Gate::allows('update', $post)` or `$this->authorize('update', $post);`
- **Before Hooks:** Policies can use `before()` to grant/deny access globally (e.g., for admins).

---

## Validation & Forms

### Q8: How does Laravel validation work and what are Form Requests?
**Answer:** Laravel validates incoming HTTP requests using a fluent rules API. Form Requests are dedicated classes that encapsulate validation logic, keeping controllers clean.

**Example:**
```php
class StoreUserRequest extends FormRequest {
    public function rules(): array {
        return ['email' => 'required|email|unique:users,email', 'password' => 'required|min:8|confirmed'];
    }
    public function messages(): array {
        return ['password.min' => 'Password must be at least 8 characters.'];
    }
}
```
**Benefits:** Automatic redirection with errors, `$request->validated()` returns only safe data, supports `after` hooks, and integrates with `Form::` or Blade seamlessly.

---

### How to ensure that data validation is automatically triggered when handling form submissions. What method will best achieve this by injecting the form request into a controller?

**Answer:** Create a custom Form Request class via `php artisan make:request StoreExampleRequest`, define your rules in its `rules()` method, and type-hint that class in your controller method. Laravel's service container intercepts the type-hint, instantiates the Form Request, runs validation, and automatically redirects back with errors if it fails.

---

### Q9: How do you handle file uploads and form method spoofing in Laravel?
**Answer:**
- **File Uploads:** HTML forms require `enctype="multipart/form-data"`. Laravel handles uploads via `$request->file('photo')` and stores them using `$request->file('photo')->store('path')` (uses Storage facade).
- **Method Spoofing:** HTML forms only support `GET`/`POST`. Laravel uses `_method` hidden field (`@method('PUT')`) to simulate `PUT`, `PATCH`, or `DELETE` routes, which are routed correctly by the framework.

---

## Advanced Laravel & Performance

### Q10: What is Laravel Octane and how does it improve performance?
**Answer:** Octane boosts Laravel performance by running the application in a long-lived process using **Swoole** or **RoadRunner**, instead of booting from scratch on every request.

**Key Features:**
- Keeps app, config, and DI container in memory between requests.
- Concurrency handling (Swoole supports parallel requests).
- Requires careful handling of mutable state (reset singletons, clear resolved instances between requests via `Octane::tick()`).
- Best for high-traffic APIs, real-time apps, or when PHP-FPM bootstrapping becomes a bottleneck.

---

### Q11: What is Laravel Horizon and how does it help with queues?
**Answer:** Horizon is a dashboard and configuration system for Laravel's Redis queues.

**Features:**
- Real-time monitoring of jobs, failed jobs, and queue workers.
- Auto-scaling workers based on queue load.
- Metrics & throughput tracking.
- Configurable balance strategies (`auto`, `simple`, `false`).
- **Setup:** Requires Redis, `composer require laravel/horizon`, `php artisan horizon:install`, and `php artisan horizon`.

---

### Q12: How does Laravel handle caching and what are cache tags?
**Answer:** Laravel supports multiple cache drivers (Redis, Memcached, File, Database). Cache tags allow grouping and invalidating related cache items.

```php
Cache::tags(['posts', 'author:1'])->put('post_5', $data, 3600);
Cache::tags(['posts'])->flush(); // Invalidates all posts, keeps other tags intact
```
**Note:** Cache tags require Redis or Memcached drivers. File/Database drivers do not support them.

---

## Core Architecture & Other Topics

### Q13: What is the Service Container and how does dependency injection work?
**Answer:** The Service Container is Laravel's IoC container. It manages class dependencies and performs automatic injection.

- **Binding:** `$this->app->bind(Interface::class, Implementation::class);`
- **Singleton:** `$this->app->singleton(Config::class, fn() => new Config());`
- **Resolution:** Type-hinting in constructors/controllers triggers automatic resolution.
- **Contextual Binding:** `$this->app->when(PhotoController::class)->needs(Storage::class)->give(fn() => Storage::disk('s3'));`

---

### Q14: What are Service Providers and what is the boot vs register lifecycle?
**Answer:** Service Providers are the central place to configure Laravel (bindings, middleware, routes, views, events).

- **`register()`:** Bind services to the container. Should not access other services or routes.
- **`boot()`:** Runs after all providers are registered. Safe to use other services, define routes, add view composers, or configure middleware.
- **Deferred Providers:** Only loaded when their bound service is actually requested, improving performance.

---

### Q15: How does Laravel handle database transactions and what are the best practices?
**Answer:** Use `DB::transaction()` for atomic operations.

```php
DB::transaction(function () {
    $user = User::create(['name' => 'John']);
    $user->profile()->create(['bio' => 'Developer']);
});
```
**Best Practices:**
- Keep transactions short to avoid locking.
- Handle deadlocks with `retry()` or catch `QueryException`.
- Avoid long-running external API calls inside transactions.
- Use `DB::beginTransaction()`, `commit()`, `rollBack()` for manual control when needed.

---

### Q16: What are Laravel Events & Listeners and when should you use them?
**Answer:** Events decouple application logic. An event is dispatched, and listeners react asynchronously or synchronously.

- **Use Cases:** Send emails after registration, log activity, trigger webhooks, update search indices.
- **Queueing:** Listeners can implement `ShouldQueue` to run asynchronously.
- **Event Subscribers:** Group related listeners into a single class.
- **Note:** Overusing events can make code harder to trace. Use for cross-cutting concerns, not core business logic.

---

### How to enhance application performance by configuring separate connections for read and write hosts. Which configuration file setting will best achieve this?

**Answer:** Configure the read and write arrays inside your database connection in `config/database.php`. Laravel automatically routes `SELECT` queries to the read host and `INSERT/UPDATE/DELETE` queries to the write host.

---

## 📚 References

1. [Laravel 11 Documentation](https://laravel.com/docs/11.x)
2. [Eloquent Relationships](https://laravel.com/docs/11.x/eloquent-relationships)
3. [Validation](https://laravel.com/docs/11.x/validation)
4. [Authorization (Gates & Policies)](https://laravel.com/docs/11.x/authorization)
5. [Sanctum Documentation](https://laravel.com/docs/11.x/sanctum)
6. [Octane Documentation](https://laravel.com/docs/11.x/octane)
7. [Horizon Documentation](https://laravel.com/docs/11.x/horizon)
8. [Service Container](https://laravel.com/docs/11.x/container)
9. [CSRF Protection](https://laravel.com/docs/11.x/csrf)
10. [Laravel Best Practices (Spatie)](https://github.com/spatie/laravel-best-practices)
