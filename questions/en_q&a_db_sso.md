# Single Sign-On (SSO) Interview Questions & Answers

## 📚 Table of Contents
- [Fundamentals & Architecture](#fundamentals--architecture)
- [Protocols & Standards](#protocols--standards)
- [Security & Token Management](#security--token-management)
- [Implementation & Integration](#implementation--integration)
- [Troubleshooting & Best Practices](#troubleshooting--best-practices)
- [📊 Quick Reference](#-quick-reference)
- [📚 References](#-references)

---

## Fundamentals & Architecture

### Q1: What is Single Sign-On (SSO) and how does it differ from traditional authentication?
**Answer:** SSO allows users to authenticate once with an Identity Provider (IdP) and gain access to multiple independent applications (Service Providers/Relying Parties) without re-entering credentials. Traditional authentication requires separate login flows per application. SSO centralizes identity management, improves UX, reduces password fatigue, and enables centralized session control.

---

### Q2: Explain the roles of Identity Provider (IdP) and Service Provider (SP) / Relying Party (RP).
**Answer:** 
- **IdP:** Authenticates users, maintains identity directories, issues tokens/assertions, and enforces auth policies.
- **SP/RP:** The application requesting authentication. Trusts the IdP, consumes tokens/assertions, and grants access based on validated claims.
**Relationship:** Trust is established via metadata exchange, certificate signing, and predefined trust relationships.

---

### Q3: What are the main benefits and risks of implementing SSO?
**Answer:** 
**Benefits:** Reduced password fatigue, centralized access control, faster onboarding/offboarding, improved security posture (MFA, anomaly detection at IdP), better auditability.
**Risks:** Single point of failure (IdP outage blocks all apps), compromised IdP = compromised ecosystem, complex integration/metadata management, potential session hijacking if tokens aren't secured properly.

---

## Protocols & Standards

### Q4: Compare SAML 2.0 and OpenID Connect (OIDC). When would you choose one over the other?
**Answer:** 
| Feature | SAML 2.0 | OpenID Connect (OIDC) |
| :--- | :--- | :--- |
| **Data Format** | XML | JSON (JWT) |
| **Complexity** | Heavy, verbose, strict schema | Lightweight, developer-friendly |
| **Primary Use** | Enterprise SSO, legacy systems | Modern web/mobile apps, APIs |
| **Token Type** | SAML Assertion | ID Token (JWT) + Access Token |
| **Flow** | Browser-based redirects + POST bindings | OAuth 2.0 flows (Auth Code, PKCE, Implicit) |
| **Choose When** | Integrating with enterprise IdPs (ADFS, Okta legacy), compliance-heavy environments | Building new apps, SPAs, mobile, microservices, API-first architectures |

---

### Q5: How does OAuth 2.0 relate to SSO, and why is OIDC preferred over plain OAuth for authentication?
**Answer:** OAuth 2.0 is an **authorization** framework (delegates access to resources). It doesn't standardize identity verification. OIDC is an **authentication** layer built on OAuth 2.0. It adds:
- Standardized ID Token with verified user claims (`sub`, `iss`, `aud`, `exp`)
- `/userinfo` endpoint
- Standardized scopes (`openid`, `profile`, `email`)
- Security extensions (`nonce`, `state`, PKCE)
Plain OAuth leaves identity implementation to vendors, causing fragmentation and security gaps. OIDC solves this with a universal standard.

---

### Q6: Explain the difference between IdP-initiated and SP-initiated SSO flows.
**Answer:** 
- **SP-Initiated:** User visits app → app redirects to IdP → IdP authenticates → IdP redirects back to app with token/assertion. Most common, allows app to preserve original request context.
- **IdP-Initiated:** User logs into IdP dashboard → clicks app tile → IdP sends token/assertion directly to app. Simpler for users but harder to preserve deep links or original request state. Often used in enterprise portals.

---

## Security & Token Management

### Q7: How are SSO tokens validated, and what cryptographic mechanisms ensure their integrity?
**Answer:** 
- **SAML:** XML signatures using RSA/DSA. SP validates `<Signature>` against IdP's public certificate.
- **OIDC:** JWT signature validated via RS256/ES256/PS256. SP fetches IdP's JWKS (`/.well-known/openid-configuration/jwks`) to verify `kid` (key ID).
- **Validation Steps:** Check signature → verify `iss` (issuer) → validate `aud` (audience) → check `exp`/`nbf` → validate `nonce` (OIDC) → verify signature algorithm matches trust configuration.

---

### Q8: What is clock skew in SSO, and how do you handle it?
**Answer:** Clock skew is the time difference between IdP and SP servers. If clocks drift, tokens may appear expired (`exp`) or not-yet-valid (`nbf`), causing login failures.
**Handling:** 
- Allow configurable tolerance (e.g., ±2–5 minutes)
- Sync servers via NTP
- Log and alert on skew > threshold
- Some libraries auto-compensate using `iat` (issued-at) timestamps

---

### Q9: How do you securely handle token revocation or session termination in SSO?
**Answer:** 
- **Short-lived tokens:** ID/access tokens expire quickly (5–60 min); refresh tokens rotate or expire.
- **Backchannel Logout (OIDC):** IdP sends POST to SP's logout endpoint to invalidate sessions.
- **Frontchannel Logout:** Redirects to SP logout URLs via iframe/redirect (less reliable).
- **SAML SLO:** `<LogoutRequest>`/`<LogoutResponse>` exchanges (complex, often skipped in favor of short TTL + session cookies).
**Best Practice:** Rely on short token TTL + secure refresh rotation + explicit logout endpoints rather than complex global revocation.

---

## Implementation & Integration

### Q10: Walk through the typical OIDC Authorization Code Flow with PKCE for SSO.
**Answer:** 
1. Client generates `code_verifier` and `code_challenge = SHA256(verifier)`
2. Redirects user to IdP with `response_type=code`, `client_id`, `redirect_uri`, `scope=openid`, `state`, `code_challenge`, `code_challenge_method=S256`
3. IdP authenticates user, prompts consent, redirects to `redirect_uri?code=XYZ&state=ABC`
4. Client exchanges `code` + `code_verifier` at token endpoint for `id_token`, `access_token`, `refresh_token`
5. IdP validates `code_verifier` matches original `code_challenge`, issues tokens
6. Client validates ID token, establishes session, uses access token for API calls
**Why PKCE:** Prevents authorization code interception attacks, required for SPAs/mobile, recommended everywhere.

---

### Q11: How do you handle user provisioning and attribute mapping in SSO integrations?
**Answer:** 
- **Just-in-Time (JIT) Provisioning:** Create/update user on first login using claims (`sub`, `email`, `name`, `groups`). Map IdP attributes to local schema.
- **SCIM (System for Cross-domain Identity Management):** Automate bulk/user lifecycle sync (create, update, deactivate) via REST API.
- **Attribute Mapping:** Define transforms (e.g., `email` → `username`, `groups` → `roles`, `department` → `tenant_id`). Handle missing/optional fields gracefully.
- **Conflict Resolution:** Use immutable `sub` (subject ID) as primary key; never rely on mutable claims like email for identity linkage.

---

### Q12: What are the key differences between enterprise SSO and consumer/social login?
**Answer:** 
| Aspect | Enterprise SSO | Social/Consumer Login |
| :--- | :--- | :--- |
| **IdP** | Okta, Azure AD, Keycloak, PingFederate | Google, Apple, Facebook, GitHub |
| **Control** | Centralized policy, MFA, compliance, audit | Decentralized, user-controlled, limited enterprise features |
| **Attributes** | Rich, standardized (SCIM, SAML attributes, groups) | Minimal, privacy-focused, inconsistent across providers |
| **Use Case** | Internal apps, B2B SaaS, compliance-heavy | B2C apps, rapid onboarding, social features |
| **Security** | Strict certificate rotation, IP allowlists, device trust | OAuth2/OIDC, rate limits, basic MFA |

---

## Troubleshooting & Best Practices

### Q13: A user reports "Invalid Signature" during SSO login. What are the likely causes and how do you debug?
**Answer:** 
**Causes:** 
- Expired/rotated IdP certificate not updated in SP trust store
- Mismatched `kid` in JWT header vs JWKS
- Algorithm mismatch (e.g., IdP sends `RS256`, SP expects `HS256`)
- Clock skew causing validation window mismatch
- Malformed token (truncation, double-encoding)
**Debug Steps:** 
1. Decode token header/payload (jwt.io)
2. Verify `iss`, `aud`, `exp`, `kid`
3. Fetch JWKS/metadata from IdP
4. Validate signature locally with matching public key
5. Check IdP logs for signing key rotation or misconfiguration
6. Ensure SP trust config matches IdP's current signing cert

---

### Q14: How do you implement Single Logout (SLO) and what are its challenges?
**Answer:** 
- **OIDC:** Use RP-Initiated Logout (`/logout?post_logout_redirect_uri=...&id_token_hint=...`). IdP terminates session, optionally calls back to registered `frontchannel_logout_uri` endpoints.
- **SAML:** Exchange `<LogoutRequest>`/`<LogoutResponse>` between IdP and all SPs that established sessions.
**Challenges:** 
- Not all apps support SLO endpoints
- Browser restrictions block iframe-based logout
- Race conditions with concurrent logins
- Offline/mobile apps can't participate
**Practical Approach:** Short token TTL + secure refresh rotation + explicit app logout > complex global SLO.

---

### Q15: What security best practices should be followed when implementing SSO in production?
**Answer:** 
- Enforce PKCE for all public clients (SPAs, mobile)
- Validate `state` and `nonce` to prevent CSRF/replay
- Use short-lived access tokens + refresh token rotation
- Store tokens securely (httpOnly cookies for web, secure storage for mobile)
- Rotate IdP signing keys regularly; automate JWKS/metadata refresh
- Implement MFA at IdP, not per-app
- Monitor failed logins, anomalous locations, token reuse
- Never log tokens or secrets; mask in diagnostics
- Use OIDC `max_age` or `prompt=login` for sensitive re-authentication
- Regularly audit trust relationships, certificate expirations, and claim mappings

---

## 📊 Quick Reference

| Concept | Standard | Token Type | Validation | Primary Use |
| :--- | :--- | :--- | :--- | :--- |
| **SAML 2.0** | XML-based protocol | SAML Assertion | XML Signature + Cert | Enterprise SSO, legacy |
| **OIDC** | OAuth 2.0 extension | ID Token (JWT) + Access Token | JWT Signature + JWKS | Modern web/mobile/API |
| **OAuth 2.0** | Authorization framework | Access Token (opaque/JWT) | Introspection or JWT sig | Delegated access, not auth |
| **PKCE** | RFC 7636 | Code verifier/challenge | Server-side hash match | Secure public clients |
| **SCIM 2.0** | Provisioning standard | REST/JSON | Bearer token | User lifecycle sync |

---

## 📚 References

1. [OpenID Connect Core 1.0 Specification](https://openid.net/specs/openid-connect-core-1_0.html)
2. [SAML 2.0 Technical Overview (OASIS)](https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=security)
3. [RFC 6749: The OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
4. [RFC 7636: Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636)
5. [RFC 7519: JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
6. [NIST SP 800-63: Digital Identity Guidelines](https://pages.nist.gov/800-63-3/)
7. [Okta SSO Best Practices](https://developer.okta.com/docs/concepts/sso/)
8. [Microsoft Entra ID (Azure AD) SSO Documentation](https://learn.microsoft.com/en-us/entra/identity-platform/)
9. [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
10. [SCIM 2.0 Protocol (RFC 7644)](https://datatracker.ietf.org/doc/html/rfc7644)

---

## ✅ Self-Check

- [ ] Can I explain SSO, IdP, and SP in one clear sentence each?
- [ ] Do I know when to use SAML vs OIDC vs plain OAuth?
- [ ] Can I walk through the Auth Code + PKCE flow step-by-step?
- [ ] Do I understand JWT/SAML signature validation and clock skew handling?
- [ ] Can I troubleshoot "Invalid Signature" or "Audience Mismatch" errors?
- [ ] Do I know practical approaches to session termination vs Single Logout?

*Practice explaining these aloud. Use the quick reference table to memorize protocol differences and validation steps.*
