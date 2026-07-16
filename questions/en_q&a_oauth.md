# Auth Interview Questions: OAuth 2.0 vs OpenID Connect, Access vs ID Tokens

## 📚 Table of Contents
- [OAuth 2.0 vs OpenID Connect](#oauth-20-vs-openid-connect)
- [Access Token vs ID Token](#access-token-vs-id-token)
- [Practical Scenarios & Security](#practical-scenarios--security)
- [📊 Quick Reference](#-quick-reference)
- [💡 Interview Tips](#-interview-tips)
- [References](#references)
- [✅ Self-Check](#-self-check)

---

## OAuth 2.0 vs OpenID Connect

### Q1: What is the fundamental difference between OAuth 2.0 and OpenID Connect (OIDC)?
**Answer:** 
- **OAuth 2.0** is an **authorization** framework. It delegates access to protected resources (APIs) without sharing credentials.
- **OpenID Connect** is an **authentication** layer built on top of OAuth 2.0. It adds identity verification, standardized user info, and the ID token.

**Example:** 
- OAuth: "Allow this app to read your Google Drive files."
- OIDC: "Verify this user is john@example.com and return their name/email."

**Source:** [RFC 6749 (OAuth 2.0)](https://datatracker.ietf.org/doc/html/rfc6749), [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)

---

### Q2: Can you use OAuth 2.0 for user login? Why is OIDC preferred?
**Answer:** Historically, apps used OAuth access tokens to call a `/userinfo` endpoint for login ("OAuth for login"). This was fragile, non-standardized, and prone to security flaws. OIDC standardizes authentication with:
- A cryptographically signed **ID token**
- Standardized scopes (`openid`, `profile`, `email`)
- A dedicated `/userinfo` endpoint with consistent claims
- Built-in security extensions (PKCE, nonce, state)

**Example:** Before OIDC, Facebook and Google each had custom login flows. Now, both implement OIDC, allowing unified client libraries.

**Source:** [OAuth.net: OIDC Overview](https://oauth.net/2/openid-connect/)

---

### Q3: What are the most common grant flows in modern applications, and which one is recommended?
**Answer:**
- **Authorization Code + PKCE:** Recommended for web, mobile, and SPAs. Secure against code interception.
- **Client Credentials:** Machine-to-machine (no user context).
- **Refresh Token Grant:** Silently renew access tokens.
- ~~Implicit Grant~~: Deprecated due to security risks (tokens exposed in browser URLs/history).

**Example:** A React SPA uses PKCE flow: generates `code_verifier`/`code_challenge`, exchanges authorization code for tokens via a secure backend proxy or direct PKCE exchange.

**Source:** [RFC 8252 (OAuth 2.0 for Native Apps)](https://datatracker.ietf.org/doc/html/rfc8252), [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)

---

## Access Token vs ID Token

### Q4: What is the purpose of an Access Token vs an ID Token?
**Answer:**
- **Access Token:** Proves **authorization** to access an API/resource server. Contains scopes/permissions. Can be opaque or JWT.
- **ID Token:** Proves **authentication** (who the user is). Always a JWT. Intended for the client application, not the API.

**Example:** 
- Access Token: `"scope": "read:invoices write:invoices"` → sent to `/api/invoices`
- ID Token: `"sub": "usr_123", "email": "jane@corp.com"` → parsed by frontend to show user profile

**Source:** [OpenID Connect Core §2](https://openid.net/specs/openid-connect-core-1_0.html#Overview)

---

### Q5: How do you validate each token, and who is responsible?
**Answer:**
- **Access Token:** Validated by the **resource server** (API). Checks signature, `exp`, `aud`, `scope`, and issuer. Opaque tokens are introspected via `/token/introspect`.
- **ID Token:** Validated by the **client application**. Checks signature, `iss`, `aud`, `exp`, `nonce`, and `auth_time`. Never sent to APIs.

**Example:** 
```http
# Client validates ID token locally (JWT)
jwt.verify(idToken, publicKey, { audience: 'my-app-client-id' });

# API validates access token
POST /oauth/introspect
Authorization: Bearer <access_token>
```

**Source:** [RFC 7519 (JWT)](https://datatracker.ietf.org/doc/html/rfc7519), [RFC 7662 (Token Introspection)](https://datatracker.ietf.org/doc/html/rfc7662)

---

### Q6: Why should you never use an ID token to call an API?
**Answer:** 
- ID tokens lack **scopes/permissions** (authorization context)
- They may contain **sensitive PII** (email, name) that shouldn't traverse APIs
- APIs expect access tokens with audience (`aud`) matching the API, not the client
- Breaks security separation: authentication ≠ authorization

**Example Risk:** A frontend sends an ID token to `/api/admin/users`. The API can't verify if the user has `admin:write` scope, leading to privilege escalation.

**Source:** [Auth0: ID Token vs Access Token](https://auth0.com/docs/get-started/authentication-and-authorization-flow/id-tokens-vs-access-tokens)

---

## Practical Scenarios & Security

### Q7: How does PKCE prevent authorization code interception attacks?
**Answer:** PKCE (Proof Key for Code Exchange) adds a dynamically generated `code_verifier` and its SHA256 hash (`code_challenge`). The authorization server stores the challenge and only exchanges the code for tokens if the verifier matches. Prevents malicious apps from stealing authorization codes.

**Flow:**
```http
1. Client generates: code_verifier = "random-string-128-chars"
2. Client sends: code_challenge = base64url(sha256(verifier))
3. Auth server returns: authorization_code
4. Client exchanges code + code_verifier for tokens
```

**Source:** [RFC 7636 (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636)

---

### Q8: When should you use opaque tokens vs JWTs for access tokens?
**Answer:**
- **JWT:** Stateless validation, good for microservices, contains claims/scopes. Larger size, harder to revoke instantly.
- **Opaque:** Stateful, validated via introspection. Smaller, instantly revocable, better for high-security/internal APIs.

**Recommendation:** Use JWTs for public APIs with short TTL (5-15 min). Use opaque tokens for sensitive systems or when immediate revocation is required.

**Source:** [OAuth 2.0 Token Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)

---

### Q9: How do you securely handle token refresh in SPAs?
**Answer:** 
- Store refresh tokens in **httpOnly, secure, SameSite cookies** (not localStorage)
- Implement **refresh token rotation** (new refresh token issued on each use; old one invalidated)
- Detect reuse → revoke entire token family
- Use backend-for-frontend (BFF) pattern to keep tokens server-side

**Example:** 
```javascript
// BFF endpoint
app.post('/api/refresh', async (req, res) => {
  const newTokens = await authProvider.rotateRefreshToken(req.cookies.refresh);
  res.cookie('refresh', newTokens.refresh, { httpOnly: true, secure: true });
  res.json({ accessToken: newTokens.access });
});
```

**Source:** [RFC 6819 (OAuth 2.0 Threat Model)](https://datatracker.ietf.org/doc/html/rfc6819), [Refresh Token Rotation](https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation)

---

##  Quick Reference

| Token / Protocol | Purpose | Format | Validated By | Contains |
| :--- | :--- | :--- | :--- | :--- |
| **OAuth Access Token** | API authorization | Opaque or JWT | Resource Server | `scope`, `exp`, `aud`, `client_id` |
| **OIDC ID Token** | User authentication | JWT only | Client App | `sub`, `name`, `email`, `nonce`, `auth_time` |
| **Refresh Token** | Obtain new access/ID tokens | Opaque (usually) | Auth Server | Long-lived, rotated, bound to session |
| **OAuth 2.0** | Delegated authorization | Protocol | N/A | Grants, scopes, tokens |
| **OpenID Connect** | Authentication + identity | Protocol extension | N/A | ID token, userinfo, standardized claims |

---

##  Interview Tips

- **Clarify context first:** Ask if they're building a SPA, mobile app, or B2B service. Security recommendations differ.
- **Emphasize separation:** "ID tokens prove *who*, access tokens prove *what they can do*. Never mix them."
- **Mention modern standards:** Reference OAuth 2.1, PKCE, BFF pattern, and token rotation to show up-to-date knowledge.
- **Discuss trade-offs:** JWT vs opaque, stateless vs stateful, convenience vs security. Interviewers love nuanced answers.
- **Use concrete examples:** "In our last project, we switched from implicit flow to PKCE + BFF to eliminate XSS token theft risks."

---

## References

1. [RFC 6749: The OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
2. [RFC 6750: The OAuth 2.0 Authorization Framework: Bearer Token Usage](https://datatracker.ietf.org/doc/html/rfc6750)
3. [RFC 7636: Proof Key for Code Exchange by OAuth Public Clients](https://datatracker.ietf.org/doc/html/rfc7636)
4. [RFC 8725: JSON Web Token Best Current Practices](https://datatracker.ietf.org/doc/html/rfc8725)
5. [OpenID Connect Core 1.0 Specification](https://openid.net/specs/openid-connect-core-1_0.html)
6. [OAuth 2.1 Draft Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)
7. [Auth0: ID Token vs Access Token](https://auth0.com/docs/get-started/authentication-and-authorization-flow/id-tokens-vs-access-tokens)
8. [OWASP: OAuth 2.0 and OpenID Connect Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)
9. [RFC 6819: OAuth 2.0 Threat Model and Security Considerations](https://datatracker.ietf.org/doc/html/rfc6819)

---

## ✅ Self-Check

- [ ] Can I explain OAuth vs OIDC in one sentence each?
- [ ] Do I know which token goes to the API vs the frontend?
- [ ] Can I describe PKCE and why implicit flow is deprecated?
- [ ] Do I understand JWT validation steps (signature, exp, aud, iss)?
- [ ] Can I design a secure token refresh strategy for an SPA?
- [ ] Do I know when to choose opaque vs JWT access tokens?

*Review these questions aloud. Simulate explaining them to a junior developer to test clarity.*
