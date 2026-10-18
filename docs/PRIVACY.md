# VERITAS AI — Privacy, Security, & Digital Rights Architecture

## 1. Core Privacy Philosophy

VERITAS AI is designed specifically to prevent mass surveillance and protect individual digital identity rights. The platform deliberately avoids crawling external websites, scraping social media feeds, or indexing biometric profiles without affirmative consent.

---

## 2. Key Privacy Guarantees

1. **Explicit Affirmative Consent:**
   - Registration of a likeness reference photograph requires explicit consent.
   - The consent timestamp is permanently logged in the database (`consent_recorded_at`).

2. **Isolated Vault Storage:**
   - Reference images and biometric embeddings are stored strictly inside `./data/identity/`.
   - This directory is **never** mounted or exposed via public static endpoints.
   - Files can only be accessed through authenticated backend handlers verifying ownership.

3. **No Biometric Data Sharing or Model Retraining:**
   - User identity profiles and uploaded media are never used to retrain neural networks without separate, legally binding agreements.

4. **Right to Immediate Data Erasure:**
   - Users can delete their reference identity image at any time (`DELETE /api/identity/profile`), which immediately deletes both the disk image and mathematical embedding.
   - Users can wipe their entire account and all forensic history (`DELETE /api/auth/me`).

---

## 3. Digital Evidence Integrity & SHA-256 Hashing

- Every media file ingested by VERITAS AI has its cryptographic SHA-256 hash computed immediately from the raw bitstream.
- **Forensic Interpretation:**
  - A matching SHA-256 hash confirms identical digital contents bit-for-bit.
  - A differing hash indicates altered bytes (e.g. video re-compression or re-encoding), but does not prove whether the underlying visual scene was manipulated.
