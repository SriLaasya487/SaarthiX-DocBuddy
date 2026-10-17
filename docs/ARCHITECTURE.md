# Technology Stack

| Need | Technology |
|---|---|
| Mobile app | Flutter or React Native (Android first) |
| Family web portal | Next.js / React |
| Backend | Python FastAPI or Node.js |
| Database | PostgreSQL with row-level security; Redis for scheduling |
| Reminders | Celery or Bull + FCM push |
| Speech (Indian languages) | Bhashini, AI4Bharat; Google/Azure fallback |
| AI assistant | Hosted LLM, strict instructions, structured output, approved tools only |
| Prescription scan | OCR + mandatory elder confirmation |
| Phone-call check-in | Exotel / Twilio / Knowlarity (IVR) |
| Family alerts | WhatsApp Business API or SMS |
| Security & hosting | Encryption, OTP login, audit trail, Indian cloud region |
| Fall detection / wearables | Phone accelerometer, BLE devices, smartwatch SDKs |
| Compliance | DPDP Act 2023 (export/delete, consent records) |

## Consent model (sketch)
- `consent(elder_id, grantee_id, data_type, scope, expires_at, revoked_at)`
- Every read passes a row-level-security check against `consent`, then writes to `access_log(who, what, when)`.
- Escalations (SOS, fall, low mood) fire only for grantees with `scope='escalation'`.
