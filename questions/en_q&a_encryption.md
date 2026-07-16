# Encryption Interview Questions: Symmetric/Asymmetric, Keys, Algorithms, Web & CAs

## 📚 Table of Contents
- [Symmetric vs Asymmetric Encryption](#symmetric-vs-asymmetric-encryption)
- [Key Types & Algorithms](#key-types--algorithms)
- [Web Usage & TLS/HTTPS](#web-usage--tlshttps)
- [Certificate Authorities & PKI](#certificate-authorities--pki)
- [📊 Quick Reference](#-quick-reference)
- [💡 Interview Tips](#-interview-tips)
- [References](#references)
- [✅ Self-Check](#-self-check)

---

## Symmetric vs Asymmetric Encryption

### Q1: What is the fundamental difference between symmetric and asymmetric encryption?
**Answer:** Symmetric encryption uses a single shared secret key for both encryption and decryption. It is fast and efficient for large data volumes. Asymmetric encryption uses a mathematically linked key pair: a public key (shared openly) and a private key (kept secret). It enables secure key exchange and digital signatures but is computationally slower.

**Example:** 
- Symmetric: AES encrypts a 10GB database backup in seconds.
- Asymmetric: RSA signs a software update so clients can verify authenticity before installing.

**Source:** [NIST SP 800-57: Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

---

### Q2: Why do modern systems use hybrid encryption instead of pure asymmetric encryption?
**Answer:** Asymmetric algorithms are 100–1000x slower than symmetric ones. Hybrid encryption combines both: asymmetric crypto securely exchanges a temporary symmetric session key, then symmetric crypto handles bulk data encryption. This achieves both security and performance.

**Example:** TLS 1.3 handshake uses ECDHE (asymmetric) to derive a shared secret, then switches to AES-256-GCM (symmetric) for all application data.

**Source:** [RFC 8446: TLS 1.3](https://datatracker.ietf.org/doc/html/rfc8446)

---

### Q3: What is Perfect Forward Secrecy (PFS) and why is it critical?
**Answer:** PFS ensures that compromise of long-term private keys does not expose past session keys. It is achieved using ephemeral key exchanges (e.g., ECDHE) where each session generates unique temporary keys. Without PFS, an attacker recording encrypted traffic could decrypt it later if they obtain the server's private key.

**Example:** Static RSA key exchange (TLS 1.2 and older) lacks PFS. Modern TLS 1.3 mandates ephemeral Diffie-Hellman variants, guaranteeing PFS by design.

**Source:** [Mozilla: Perfect Forward Secrecy](https://wiki.mozilla.org/Security/Server_Side_TLS#Perfect_Forward_Secrecy)

---

## Key Types & Algorithms

### Q4: What are the main cryptographic key types and their roles?
**Answer:** 
- **Symmetric Keys:** Shared secrets for bulk encryption (AES, ChaCha20)
- **Asymmetric Public/Private Keys:** Identity, key exchange, signatures (RSA, ECDSA, Ed25519)
- **Session Keys:** Short-lived symmetric keys derived per connection (ECDHE output)
- **Master Keys:** Long-term keys used to derive/protect other keys (KDF input, HSM-stored)
- **Data Encryption Keys (DEKs) & Key Encryption Keys (KEKs):** DEKs encrypt data; KEKs encrypt DEKs for safe storage

**Example:** Cloud storage uses envelope encryption: `KEK (in HSM) → encrypts → DEK → encrypts → object`

**Source:** [AWS: Envelope Encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping)

---

### Q5: Which encryption algorithms are recommended today, and which are deprecated?
**Answer:** 
- **✅ Recommended:** AES-256-GCM, ChaCha20-Poly1305 (AEAD ciphers), X25519/Ed25519 (ECDH/EdDSA), SHA-256/SHA-3, HKDF, Argon2id
- **⚠️ Deprecated/Avoid:** DES/3DES, RC4, MD5, SHA-1, RSA key exchange (static), ECB mode, PBKDF1

**Rule of Thumb:** Prefer AEAD ciphers, elliptic curves over RSA, and memory-hard KDFs for passwords.

**Source:** [NIST Cryptographic Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines), [RFC 8446 Appendix B](https://datatracker.ietf.org/doc/html/rfc8446#appendix-B.2)

---

### Q6: How do you securely store passwords vs sensitive data?
**Answer:** 
- **Passwords:** Never encrypt. Use adaptive, memory-hard hashing (Argon2id, scrypt, bcrypt) with unique per-user salts.
- **Sensitive Data:** Encrypt with AES-256-GCM or ChaCha20-Poly1305 using envelope encryption. Store keys in KMS/HSM. Rotate keys periodically.

**Example:** 
```python
# Password hashing (not encryption)
import argon2
hasher = argon2.PasswordHasher()
stored_hash = hasher.hash(password)

# Data encryption
from cryptography.fernet import Fernet
key = Fernet.generate_key()
cipher = Fernet(key)
encrypted = cipher.encrypt(b"sensitive_data")
```

**Source:** [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

---

## Web Usage & TLS/HTTPS

### Q7: How does TLS use encryption to secure web traffic?
**Answer:** TLS establishes a secure channel through a handshake:
1. Client & server negotiate protocol version & cipher suite
2. Server presents certificate (proves identity via public key)
3. Ephemeral key exchange (ECDHE) derives shared symmetric keys
4. Both sides switch to AEAD symmetric encryption for all HTTP data
5. MAC/AEAD ensures integrity & authenticity

**Key Point:** TLS 1.3 reduces handshake to 1-RTT, removes weak ciphers, and enforces PFS.

**Source:** [Cloudflare: TLS Handshake Explained](https://www.cloudflare.com/learning/ssl/what-happens-in-a-tls-handshake/)

---

### Q8: What is the difference between transport encryption and data-at-rest encryption?
**Answer:** 
- **Transport (TLS/HTTPS):** Protects data in transit between client and server. Prevents eavesdropping/man-in-the-middle.
- **Data-at-Rest:** Protects stored data (DBs, disks, backups). Uses AES-256, TDE, or application-level encryption. Prevents unauthorized access if storage is compromised.

**Best Practice:** Use both. TLS alone doesn't protect against DB breaches or stolen backups.

**Source:** [CIS Controls: Data Protection](https://www.cisecurity.org/controls/cis-controls-list)

---

### Q9: How do you handle encryption key rotation in production?
**Answer:** 
- Use envelope encryption so only KEKs need rotation
- Maintain key versioning; decrypt with old keys, re-encrypt with new
- Automate via KMS (AWS KMS, HashiCorp Vault, GCP Cloud KMS)
- Never rotate active session keys mid-connection; rely on TLS renegotiation/reconnection
- Log rotation events for auditability

**Example:** Database field encryption uses `key_v1` for existing records, `key_v2` for new records. Background job gradually re-encrypts old data.

**Source:** [Google Cloud: Key Management Best Practices](https://cloud.google.com/kms/docs/best-practices)

---

## Certificate Authorities & PKI

### Q10: What is a Certificate Authority (CA) and how does the trust chain work?
**Answer:** A CA issues and signs digital certificates that bind public keys to identities (domains, organizations). Trust flows hierarchically:
- **Root CA:** Self-signed, pre-installed in OS/browser trust stores
- **Intermediate CA:** Signed by root, issues end-entity certificates
- **End-Entity Certificate:** Binds domain to public key, signed by intermediate

Clients verify the chain back to a trusted root. Compromise of an intermediate doesn't break root trust.

**Source:** [RFC 5280: X.509 Certificate Profile](https://datatracker.ietf.org/doc/html/rfc5280)

---

### Q11: How are certificates validated and revoked?
**Answer:** 
- **Validation:** Checks signature chain, expiration, hostname match, key usage, and revocation status
- **Revocation Methods:** 
  - **CRL (Certificate Revocation List):** Periodic signed list of revoked serial numbers
  - **OCSP (Online Certificate Status Protocol):** Real-time query to CA responder
  - **OCSP Stapling:** Server fetches OCSP response and attaches it to TLS handshake (improves performance & privacy)

**Note:** Many browsers now prefer CT (Certificate Transparency) logs + stapling over traditional OCSP.

**Source:** [CA/Browser Forum Baseline Requirements](https://cabforum.org/baseline-requirements-documents/)

---

### Q12: What is Certificate Transparency (CT) and why does it matter?
**Answer:** CT is a public, append-only log system where all issued TLS certificates must be recorded. It prevents rogue or misissued certificates from going undetected. Browsers reject certificates not logged in CT.

**Example:** If a CA accidentally issues `*.google.com` to an attacker, CT monitors (like `crt.sh`) alert domain owners immediately.

**Source:** [RFC 6962: Certificate Transparency](https://datatracker.ietf.org/doc/html/rfc6962)

---

## 📊 Quick Reference

| Component | Type | Purpose | Modern Standard |
| :--- | :--- | :--- | :--- |
| **Bulk Encryption** | Symmetric | Data confidentiality | AES-256-GCM, ChaCha20-Poly1305 |
| **Key Exchange** | Asymmetric | Secure session key derivation | X25519, ECDHE (P-256) |
| **Digital Signatures** | Asymmetric | Authentication & integrity | Ed25519, ECDSA (P-256) |
| **Password Storage** | Hash + KDF | Irreversible credential protection | Argon2id, bcrypt, scrypt |
| **TLS Version** | Protocol | Transport security | TLS 1.3 (mandatory PFS, AEAD) |
| **Certificate Validation** | PKI | Domain/identity binding | X.509 v3 + OCSP Stapling + CT |
| **Key Storage** | Infrastructure | Secure key lifecycle | KMS/HSM, envelope encryption |

---

##  Interview Tips

- **Clarify context:** Ask if they mean web APIs, mobile SDKs, internal microservices, or compliance-heavy environments (PCI, HIPAA). Requirements differ.
- **Emphasize defense-in-depth:** "TLS protects transit, but we also encrypt DB fields and rotate keys quarterly. Defense isn't single-layer."
- **Mention modern defaults:** Reference TLS 1.3, AEAD ciphers, Ed25519, Argon2id, and KMS automation to show current practices.
- **Discuss failure modes:** Explain how you handle expired certs, CA outages, key compromise, or algorithm deprecation.
- **Avoid crypto-washing:** "We don't roll our own crypto. We use vetted libraries (libsodium, BoringSSL) and follow NIST/IETF guidelines."

---

## References

1. [RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3](https://datatracker.ietf.org/doc/html/rfc8446)
2. [RFC 5280: Internet X.509 Public Key Infrastructure](https://datatracker.ietf.org/doc/html/rfc5280)
3. [RFC 6962: Certificate Transparency](https://datatracker.ietf.org/doc/html/rfc6962)
4. [NIST SP 800-57: Key Management Guidelines](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
5. [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
6. [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
7. [Let's Encrypt: How It Works](https://letsencrypt.org/how-it-works/)
8. [AWS Key Management Service Concepts](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html)
9. [CA/Browser Forum Baseline Requirements](https://cabforum.org/baseline-requirements-documents/)
10. [IETF: Recommendations for Secure Use of TLS](https://datatracker.ietf.org/doc/html/rfc7525)

---

## ✅ Self-Check

- [ ] Can I explain why hybrid encryption is used instead of pure asymmetric?
- [ ] Do I know the difference between AES-GCM, ChaCha20, and RSA/ECDHE roles?
- [ ] Can I describe the TLS 1.3 handshake and why PFS is mandatory?
- [ ] Do I understand how certificate chains, OCSP stapling, and CT logs work together?
- [ ] Can I design a key rotation strategy for encrypted database fields?
- [ ] Do I know which algorithms are deprecated and what to use instead?

*Practice explaining these concepts aloud. Use the quick reference table to memorize algorithm roles and modern standards.*
