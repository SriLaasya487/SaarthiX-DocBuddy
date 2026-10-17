# Implementation map: all 90 features

Every row is checked by `backend/tests/test_registry.py`: the catalogue ID must exist, every listed endpoint must exist in the API, and every UI file must exist.

**Works locally** = runs and is covered by tests without any outside account. **Needs** = what you must connect/verify before it works in the real world.

| ID | Feature | API | UI | Needs outside the code |
|---|---|---|---|---|
| DB-001 | Voice-first interface | - | `voice.js`<br>`pages/ElderApp.jsx` | nothing (works locally) |
| DB-002 | Sign up by talking | `POST /auth/request-otp`<br>`POST /auth/verify` | `pages/Login.jsx` | nothing (works locally) |
| DB-003 | Daily voice check-in | `POST /checkin`<br>`GET /checkin` | `pages/CheckIn.jsx` | nothing (works locally) |
| DB-004 | Medicine reminders | `GET /medicines/due`<br>`POST /medicines/{mid}/taken`<br>`POST /medicines` | `pages/Medicines.jsx` | nothing (works locally) |
| DB-005 | Appointment reminders | `GET /appointments/due`<br>`POST /appointments`<br>`GET /appointments` | `pages/Health.jsx`<br>`pages/ElderApp.jsx` | nothing (works locally) |
| DB-006 | Doctor-type suggestion | `POST /doctor/suggest` | `pages/Doctor.jsx` | nothing (works locally) |
| DB-007 | Progress reports | `GET /reports/{period}` | `pages/Health.jsx`<br>`pages/FamilyPortal.jsx` | nothing (works locally) |
| DB-008 | Approved-only family view | `GET /family/elders`<br>`GET /family/elders/{elder_id}/summary` | `pages/FamilyPortal.jsx` | nothing (works locally) |
| DB-009 | Consent-gated alerts | `POST /alerts/{aid}/respond`<br>`GET /alerts` | `pages/CheckIn.jsx` | nothing (works locally) |
| DB-010 | Family web portal | `GET /family/elders/{elder_id}/summary` | `pages/FamilyPortal.jsx` | nothing (works locally) |
| DB-011 | 'Hear it again' and 'Slow down' buttons | - | `voice.js`<br>`pages/ElderApp.jsx` | nothing (works locally) |
| DB-012 | Voice confirmation of important answers | `POST /vitals/voice`<br>`GET /pending`<br>`POST /pending/{pid}` | `pages/Pending.jsx`<br>`voice.js` | nothing (works locally) |
| DB-013 | Gentle snooze and repeat reminders | `POST /medicines/{mid}/snooze`<br>`GET /medicines/due` | `pages/Medicines.jsx` | nothing (works locally) |
| DB-014 | Medicine stock alert | `GET /medicines` | `pages/Medicines.jsx` | nothing (works locally) |
| DB-015 | Daily 'I'm fine' message | `POST /imfine` | `pages/ElderApp.jsx` | nothing (works locally) |
| DB-016 | Festival and birthday greetings | `GET /reminders/today`<br>`POST /reminders` | `pages/Companion.jsx`<br>`pages/ElderApp.jsx` | nothing (works locally) |
| DB-017 | Emergency card | `GET /emergency-card`<br>`PUT /emergency-card`<br>`GET /emergency-card/print` | `pages/Health.jsx` | nothing (works locally) |
| DB-018 | Prescription photo scan | `POST /prescriptions/parse`<br>`POST /prescriptions/scan`<br>`GET /pending`<br>`POST /pending/{pid}` | `pages/Medicines.jsx`<br>`pages/Pending.jsx` | optional server OCR: pytesseract |
| DB-019 | Gentle pattern spotting | `GET /insights/patterns` | `pages/Companion.jsx` | nothing (works locally) |
| DB-020 | Medicine interaction information | `GET /medicines/interactions` | `pages/Medicines.jsx` | nothing (works locally) |
| DB-021 | Companionship mode | `POST /companion/chat`<br>`GET /companion/music` | `pages/Companion.jsx` | optional LLM_API_KEY for AI chat |
| DB-022 | Memory games | `GET /games`<br>`GET /games/{game}/round`<br>`POST /games/{game}/score` | `pages/Companion.jsx` | nothing (works locally) |
| DB-023 | Overwhelm/anxiety step-by-step help | `GET /calm/steps` | `pages/Companion.jsx` | nothing (works locally) |
| DB-024 | Daily 'call your parents' nudge | `GET /family/call-nudges`<br>`POST /family/elders/{elder_id}/called` | `pages/CareTeam.jsx` | nothing (works locally) |
| DB-025 | Phone-call (IVR) check-in | `POST /ivr/incoming`<br>`POST /ivr/call/{elder_id}` | - | IVR provider (Exotel/Twilio/Knowlarity) |
| DB-026 | Family alerts via WhatsApp/SMS | `GET /inbox` | `pages/CareTeam.jsx` | WHATSAPP_TOKEN or SMS_URL |
| DB-027 | Fall detection + 'Are you okay?' | `POST /fall`<br>`POST /alerts/{aid}/respond` | `pages/FallGuard.jsx` | nothing (works locally) |
| DB-028 | Vitals logging by voice | `POST /vitals`<br>`POST /vitals/voice`<br>`GET /vitals` | `pages/Health.jsx` | nothing (works locally) |
| DB-029 | Bluetooth device sync | `POST /devices`<br>`GET /devices`<br>`POST /devices/readings` | `bluetooth.js`<br>`pages/Settings.jsx` | Web Bluetooth (Chrome/Android) |
| DB-030 | Hydration, meal and walk nudges | `GET /nudges/due`<br>`PUT /settings` | `pages/Settings.jsx`<br>`pages/ElderApp.jsx` | nothing (works locally) |
| DB-031 | Sleep and activity summary | `POST /activity`<br>`GET /activity/summary` | `pages/Settings.jsx` | nothing (works locally) |
| DB-032 | Post-hospital recovery mode | `POST /recovery`<br>`GET /recovery`<br>`POST /recovery/tick` | `pages/Records.jsx` | nothing (works locally) |
| DB-033 | Symptom diary | `POST /symptoms`<br>`GET /symptoms`<br>`DELETE /symptoms/{sid}` | `pages/Records.jsx` | nothing (works locally) |
| DB-034 | Pill-box photo verification | `POST /pillbox/verify` | `pillvision.js`<br>`pages/Medicines.jsx` | nothing (works locally) |
| DB-035 | Generic alternative info | `GET /medicines/generic/{name}` | `pages/Medicines.jsx` | nothing (works locally) |
| DB-036 | Refill and pharmacy integration | `POST /refills`<br>`POST /refills/{rid}/confirm` | `pages/Medicines.jsx` | pharmacy WhatsApp number in Settings |
| DB-037 | 'Missed dose' guidance | `POST /medicines/{mid}/missed` | `pages/Medicines.jsx` | nothing (works locally) |
| DB-038 | Pre-visit summary | `GET /previsit`<br>`GET /previsit/print`<br>`POST /previsit/questions`<br>`GET /doctor/patients/{elder_id}/previsit`<br>`POST /consents/share-with-doctor` | `pages/Records.jsx` | nothing (works locally) |
| DB-039 | Post-visit voice notes | `POST /visit-notes`<br>`POST /pending/{pid}` | `pages/Records.jsx` | nothing (works locally) |
| DB-040 | Lab report reader | `POST /labs/read` | `pages/Records.jsx` | nothing (works locally) |
| DB-041 | Medical records locker | `POST /documents`<br>`GET /documents`<br>`GET /documents/search`<br>`GET /documents/{did}` | `pages/Records.jsx` | nothing (works locally) |
| DB-042 | Teleconsult booking | `POST /teleconsult/book`<br>`GET /teleconsult/join` | `pages/Records.jsx` | nothing (works locally) |
| DB-043 | Vaccination reminders | `GET /vaccinations`<br>`POST /vaccinations/done` | `pages/Records.jsx` | nothing (works locally) |
| DB-044 | Annual check-up planner | `GET /checkups`<br>`POST /checkups/done` | `pages/Records.jsx` | nothing (works locally) |
| DB-045 | Mood trends over time | `GET /insights/mood`<br>`POST /checkin` | `pages/Companion.jsx`<br>`pages/FamilyPortal.jsx` | nothing (works locally) |
| DB-046 | Guided breathing and calming audio | `GET /calm/breathing` | `pages/Companion.jsx` | nothing (works locally) |
| DB-047 | Devotional content | `GET /devotional` | `pages/Companion.jsx` | nothing (works locally) |
| DB-048 | Life-story recorder | `POST /life-stories`<br>`GET /life-stories`<br>`GET /life-stories/{sid}/audio` | `pages/Companion.jsx` | nothing (works locally) |
| DB-049 | Voice-based cognitive screening | `GET /cognitive/start`<br>`POST /cognitive/submit` | `pages/Companion.jsx` | nothing (works locally) |
| DB-050 | Adaptive memory games | `GET /games/{game}/round`<br>`POST /games/{game}/score` | `pages/Companion.jsx` | nothing (works locally) |
| DB-051 | Peer community (satsang rooms) | `GET /community/rooms`<br>`POST /community/join`<br>`POST /community/rooms/{rid}/posts`<br>`GET /community/rooms/{rid}/posts`<br>`POST /community/posts/{pid}/report`<br>`GET /community/moderation` | `pages/Community.jsx` | nothing (works locally) |
| DB-052 | Grandchild connection | `POST /messages`<br>`GET /messages`<br>`GET /messages/{mid}/file` | `pages/Companion.jsx`<br>`pages/CareTeam.jsx` | nothing (works locally) |
| DB-053 | Multiple caregivers with roles | `POST /care-team/invite`<br>`GET /care-team`<br>`POST /care-team/handover`<br>`GET /consents/proposals`<br>`POST /consents/proposals/{pid}` | `pages/CareTeam.jsx`<br>`pages/Sharing.jsx` | nothing (works locally) |
| DB-054 | Care task board | `POST /tasks`<br>`GET /tasks`<br>`POST /tasks/{tid}` | `pages/CareTeam.jsx` | nothing (works locally) |
| DB-055 | Cost sharing tracker | `POST /expenses`<br>`GET /expenses`<br>`POST /expenses/settle` | `pages/CareTeam.jsx` | nothing (works locally) |
| DB-056 | Video call from the app | `POST /video/call/{elder_id}`<br>`GET /video/incoming`<br>`POST /video/{vid}` | `pages/CareTeam.jsx`<br>`pages/ElderApp.jsx` | nothing (works locally) |
| DB-057 | Weekly 'good news' digest | `GET /family/elders/{elder_id}/digest` | `pages/FamilyPortal.jsx` | nothing (works locally) |
| DB-058 | Caregiver burnout check | `GET /caregiver/wellbeing/questions`<br>`POST /caregiver/wellbeing` | `pages/CareTeam.jsx` | nothing (works locally) |
| DB-059 | NRI mode | `POST /services`<br>`GET /services/pending`<br>`POST /services/{sid}`<br>`GET /family/elders` | `pages/CareTeam.jsx` | payment provider for real payments |
| DB-060 | SOS by voice and button | `POST /sos` | `pages/SosButton.jsx` | SMS/WhatsApp for delivery |
| DB-061 | Nearest hospital and pharmacy finder | `GET /finder/{kind}` | `pages/SafetyHub.jsx` | OpenStreetMap Overpass (free) |
| DB-062 | Trusted neighbour contact | `POST /care-team/invite`<br>`PATCH /care-team/{elder_id}/{member_id}` | `pages/CareTeam.jsx`<br>`pages/Sharing.jsx` | nothing (works locally) |
| DB-063 | Scam and fraud protection | `POST /scam/check`<br>`GET /scam/tips` | `pages/SafetyHub.jsx` | nothing (works locally) |
| DB-064 | Home safety checklist | `GET /home-safety`<br>`POST /home-safety` | `pages/SafetyHub.jsx` | nothing (works locally) |
| DB-065 | Heat, cold and pollution alerts | `GET /weather/advice` | `pages/SafetyHub.jsx` | Open-Meteo (free) |
| DB-066 | Disaster mode | `GET /disaster`<br>`POST /disaster` | `pages/SafetyHub.jsx` | nothing (works locally) |
| DB-067 | Voice assistant for small tasks | `POST /assistant/intent` | `pages/Assistant.jsx` | nothing (works locally) |
| DB-068 | Helpline directory | `GET /helplines`<br>`POST /helplines`<br>`DELETE /helplines/{number}` | `pages/SafetyHub.jsx` | nothing (works locally) |
| DB-069 | Government scheme finder | `GET /schemes` | `pages/Daily.jsx` | re-verify data/catalogue before release |
| DB-070 | Document organiser | `POST /documents`<br>`GET /documents/expiring` | `pages/Records.jsx` | nothing (works locally) |
| DB-071 | Insurance helper | `GET /insurance` | `pages/Records.jsx` | nothing (works locally) |
| DB-072 | Digital literacy coach | `GET /lessons`<br>`GET /lessons/{lid}` | `pages/Daily.jsx` | nothing (works locally) |
| DB-073 | Newspaper read-aloud | `GET /news` | `pages/Companion.jsx` | internet for RSS |
| DB-074 | Offline mode | `POST /sync/batch`<br>`GET /lite/home` | `offline.js`<br>`../public/sw.js` | nothing (works locally) |
| DB-075 | Dialect and accent support | `GET /dialect/lexicon`<br>`POST /dialect/normalize`<br>`POST /dialect/feedback` | `voice.js`<br>`pages/Settings.jsx` | field testing with real elders |
| DB-076 | Low-end phone optimization | `GET /lite/home` | `a11y.js`<br>`styles.css` | nothing (works locally) |
| DB-077 | Hearing and vision adaptations | `GET /settings`<br>`PUT /settings` | `a11y.js`<br>`pages/Settings.jsx` | nothing (works locally) |
| DB-078 | Smart speaker and wearable support | `POST /speaker/webhook`<br>`POST /wearables/push`<br>`POST /devices` | `pages/Settings.jsx` | Alexa/Google skill pointing at /speaker/webhook |
| DB-079 | Feature phone / IVR as primary channel | `POST /ivr/incoming`<br>`PATCH /me` | `pages/Settings.jsx` | IVR provider |
| DB-080 | Caregiver-assisted setup | `POST /care-team/invite`<br>`GET /consents/proposals`<br>`POST /consents/proposals/{pid}`<br>`GET /pending` | `pages/CareTeam.jsx`<br>`pages/Pending.jsx` | nothing (works locally) |
| DB-081 | Plain-language consent log | `GET /consents/log` | `pages/Sharing.jsx` | nothing (works locally) |
| DB-082 | Easy revoke | `POST /consents/revoke-by-voice`<br>`DELETE /consents/{cid}`<br>`POST /consents/revoke-all/{grantee_id}` | `pages/Sharing.jsx` | nothing (works locally) |
| DB-083 | Temporary sharing | `POST /consents`<br>`POST /consents/share-with-doctor` | `pages/Sharing.jsx` | nothing (works locally) |
| DB-084 | Nominee / incapacity handling | `POST /nominee/request`<br>`POST /nominee/{rid}/approve`<br>`GET /nominee/{rid}/audit`<br>`POST /nominee/{rid}/restore` | `pages/CareTeam.jsx` | nothing (works locally) |
| DB-085 | Data export and delete | `GET /me/export`<br>`DELETE /me`<br>`GET /me/consent-records` | `pages/Settings.jsx` | nothing (works locally) |
| DB-086 | Security baseline | `POST /auth/request-otp`<br>`POST /auth/verify`<br>`GET /consents/log` | `api.js` | run backend/sql/rls.sql on PostgreSQL; Indian cloud region |
| DB-087 | B2B2C partnerships | `POST /orgs`<br>`POST /orgs/join`<br>`GET /orgs/me/elders` | `pages/PartnerPortal.jsx` | nothing (works locally) |
| DB-088 | Community health worker mode | `GET /chw/elders`<br>`POST /chw/visit` | `pages/PartnerPortal.jsx` | nothing (works locally) |
| DB-089 | Anonymous aggregate insights | `GET /insights/aggregate` | `pages/PartnerPortal.jsx` | nothing (works locally) |
| DB-090 | Tiered pricing | `GET /pricing`<br>`GET /billing/{elder_id}`<br>`POST /billing/subscribe`<br>`POST /billing/webhook` | `pages/Settings.jsx` | payment provider webhook |

## Read this before you trust it: what is NOT proven by the tests

The tests prove the logic and the API contracts on SQLite with no network. They do **not** prove the following. Each needs a real-world check:

1. **Message delivery.** WhatsApp (Cloud API), SMS gateway, IVR provider and FCM calls are written (`services/notify.py`) but were never run against a live account. WhatsApp business-initiated messages need an approved template. Without credentials, messages only go to the in-app outbox (`GET /inbox`).
2. **IVR.** `POST /ivr/incoming` speaks Twilio-style TwiML. Exotel/Knowlarity use different flow formats, so an adapter may be needed. Languages depend on the provider's text-to-speech.
3. **Postgres row-level security.** `backend/sql/rls.sql` was written but not executed (tests use SQLite). Run it on a real Postgres and test it. It is a second lock behind the app's own consent checks.
4. **Bluetooth.** `bluetooth.js` implements the standard GATT blood-pressure, heart-rate, pulse-oximeter and glucose profiles. It is untested on real devices. Many Indian-market devices use vendor protocols and will not work. Web Bluetooth is Chrome/Android only (not iOS Safari).
5. **OCR and pill photos.** Prescription/lab OCR uses tesseract.js in the browser (downloads language data on first use, English only, handwriting will fail). `pillvision.js` is a simple blob counter that needs a plain background. Both only produce *candidates*; the elder confirms and the server cross-checks.
6. **Speech recognition / dialects.** Uses the browser's Web Speech API. Accuracy for regional dialects and elderly voices is unknown. `data/dialects.json` is a **starter** lexicon; real coverage requires field testing (feedback is collected via `POST /dialect/feedback`).
7. **Content that goes stale.** Government schemes (`services/content.py: SCHEMES`), lunar festival dates (`FESTIVALS_2026`), helpline numbers and vaccine/check-up lists are marked `verify` and must be re-checked by a person before each release. Prayer times are an astronomical approximation.
8. **Medical safety content is deliberately small and conservative.** The interaction list is a short sample, not a drug database. Nothing diagnoses or tells anyone what to take; lab values are only placed against typical ranges. A clinician should review all wording in `rules.py`/`content.py` before real users see it.
9. **Prices** are placeholders (`PRICE_FAMILY_INR`, `PRICE_CARE_INR`), and `ENFORCE_TIERS` defaults to off. Payment is a webhook stub (`/billing/webhook`, HMAC-signed); no payment provider is integrated.
10. **Offline.** Cached reads, queued writes and in-page dose alarms work while the app is open/installed. Alarms that fire with the app fully closed need native push (not included).
11. **Legal/regulatory.** Consent flows, export and delete are built toward India's DPDP Act, but this is not legal advice. Hosting in an Indian region, a privacy notice, grievance officer, and clinical/legal review of the nominee process are your tasks.
12. **No load, security or accessibility audit** has been done. The in-memory rate limiter does not work across several API servers (use Redis).
