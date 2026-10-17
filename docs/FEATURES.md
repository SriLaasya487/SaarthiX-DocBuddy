# DocBuddy - Complete Feature Catalog

90 features from the original solution doc plus additional proposals. ★ = prioritized.


## Core (Elder)

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-001 | Voice-first interface | Speak instead of typing, in the elder's regional language. | MVP | Original doc |
| DB-002 | Sign up by talking | Elder picks a language and says their name; no forms. | MVP | Original doc |
| DB-003 | Daily voice check-in | Five simple questions (feelings, medicines, pain, help, doctor visits) answered by voice or large buttons. | MVP | Original doc |
| DB-004 | Medicine reminders | Spoken medicine name, time, tablet count; elder taps 'I took it'. | MVP | Original doc |
| DB-005 | Appointment reminders | Spoken plus large on-screen reminders. | MVP | Original doc |
| DB-006 | Doctor-type suggestion | On a reported symptom, suggests which type of doctor to see and why. Never diagnoses. | Next | Original doc |
| DB-007 | Progress reports | Daily/weekly/monthly; private or shared, chosen by the elder. | Next | Original doc |

## Core (Family)

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-008 | Approved-only family view | Family sees only items the elder approved. | MVP | Original doc |
| DB-009 | Consent-gated alerts | App asks the elder first, then informs family only if escalation is allowed. | MVP | Original doc |
| DB-010 | Family web portal | Next.js/React portal showing permitted summaries. | Next | Original doc |

## Usability

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-011 | 'Hear it again' and 'Slow down' buttons | Replay and slower speech on any prompt. | MVP | Original doc |
| DB-012 | Voice confirmation of important answers | App reads back key answers for the elder to confirm. | MVP | Original doc |

## Medicine

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-013 | Gentle snooze and repeat reminders | Soft re-prompts when a dose is not confirmed. | MVP | Original doc |
| DB-014 | Medicine stock alert | Warns when tablets are running low. | Next | Original doc |
| DB-018 | Prescription photo scan | OCR of prescription; elder must confirm before anything is saved. | Next | Original doc |
| DB-020 | Medicine interaction information | Info only; always advises asking a doctor or pharmacist. | Later | Original doc |
| DB-034 | Pill-box photo verification | Photo of the day's tablets checked for count and colour against schedule. | Later | Added |
| DB-035 | Generic alternative info | Suggests asking the pharmacist about generics; information only. | Later | Added |
| DB-036 | Refill and pharmacy integration | Refills via 1mg, PharmEasy or local pharmacy WhatsApp, elder confirms. | Later | Added |
| DB-037 | 'Missed dose' guidance | Shows the doctor-approved instruction, never improvises. | Next | Added |

## Family

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-015 | Daily 'I'm fine' message | One-line message to family, sent with the elder's approval. | MVP | Original doc |
| DB-024 | Daily 'call your parents' nudge | Reminds children to call their parents at least once a day. | Next | Original doc |
| DB-053 | ★ Multiple caregivers with roles | Primary caregiver, siblings, doctor, neighbour with distinct permissions; weekly responsibility handover. | Next | Added |
| DB-054 | Care task board | Siblings claim tasks (e.g. 'take Dad for check-up Thursday'). | Next | Added |
| DB-055 | Cost sharing tracker | Log medical expenses and split between siblings. | Later | Added |
| DB-056 | Video call from the app | One tap; auto-answer if elder pre-approves. | Later | Added |
| DB-057 | Weekly 'good news' digest | Positive moments (walks, all medicines taken), not only alerts. | Next | Added |
| DB-058 | Caregiver burnout check | Prompts the family caregiver about their own wellbeing. | Later | Added |
| DB-059 | NRI mode | Time-zone-aware alerts; pay for local help (nurse, driver, groceries). | Scale | Added |

## Companionship

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-016 | Festival and birthday greetings | Spoken greetings for festivals and family birthdays. | Next | Original doc |
| DB-021 | Companionship mode | Music, chat and news. | Next | Original doc |

## Safety

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-017 | Emergency card | Blood group, allergies, medicines, doctor number. | MVP | Original doc |
| DB-060 | ★ SOS by voice and button | 'Help, help' or big button sends location + emergency card to chosen contacts; optional 112/ambulance call. | MVP | Added |
| DB-061 | Nearest hospital and pharmacy finder | Open-late filter, directions, call button. | Later | Added |
| DB-062 | Trusted neighbour contact | Nearby person who can reach the elder faster than family. | Next | Added |
| DB-063 | Scam and fraud protection | Warnings on bank-call/OTP/lottery scams; 'Never share your OTP'; flag suspicious calls. | Later | Added |
| DB-064 | Home safety checklist | Slippery floors, lighting, grab bars, stair rails. | Later | Added |
| DB-065 | Heat, cold and pollution alerts | Local weather and AQI advice. | Later | Added |
| DB-066 | Disaster mode | Floods/heatwaves: extra check-ins, shelter info. | Scale | Added |

## Wellbeing

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-019 | Gentle pattern spotting | E.g. tiredness reported several days in a row; informational only. | Later | Original doc |
| DB-022 | Memory games | Simple recall and attention games. | Later | Original doc |
| DB-023 | Overwhelm/anxiety step-by-step help | Simple steps to follow when overwhelmed, anxious or scared. | Next | Original doc |

## Channels

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-025 | Phone-call (IVR) check-in | Exotel/Twilio/Knowlarity IVR for check-ins. | Next | Original doc |
| DB-026 | Family alerts via WhatsApp/SMS | WhatsApp Business API or SMS, consent-gated. | Next | Original doc |

## Elder: Health

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-027 | ★ Fall detection + 'Are you okay?' | Accelerometer detects a fall; voice prompt; no reply in 60s escalates to pre-approved contacts only. | Later | Added |
| DB-028 | ★ Vitals logging by voice | 'BP is 140 over 90' is stored, charted, flagged against doctor-set ranges. | Next | Added |
| DB-029 | Bluetooth device sync | Pulls readings from glucometers, BP monitors, pulse oximeters. | Scale | Added |
| DB-030 | Hydration, meal and walk nudges | Adjustable or fully off. | Later | Added |
| DB-031 | Sleep and activity summary | Passive, opt-in only. | Later | Added |
| DB-032 | Post-hospital recovery mode | Daily checklists: wound care, diet, follow-ups. | Later | Added |
| DB-033 | Symptom diary | Spoken notes become a timeline to show the doctor. | Next | Added |

## Doctor & Records

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-038 | ★ Pre-visit summary | One-page printable/shareable note: symptoms, vitals, missed doses, questions. | Next | Added |
| DB-039 | Post-visit voice notes | Elder records doctor's advice; app converts to simple instructions after confirmation. | Later | Added |
| DB-040 | Lab report reader | Plain-language explanation of values; never diagnoses. | Later | Added |
| DB-041 | Medical records locker | Prescriptions, reports, scans; voice search ('show my last sugar test'). | Later | Added |
| DB-042 | Teleconsult booking | One-button join with a doctor or family-doctor network. | Scale | Added |
| DB-043 | Vaccination reminders | Flu, pneumonia, shingles, tetanus boosters. | Later | Added |
| DB-044 | Annual check-up planner | Eyes, hearing, dental, bone density, cholesterol. | Later | Added |

## Emotional & Cognitive

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-045 | ★ Mood trends over time | With consent, tracks check-in tone/words; alerts counselor or family if low mood persists for weeks. | Later | Added |
| DB-046 | Guided breathing and calming audio | Short audio with simple on-screen animation. | Next | Added |
| DB-047 | Devotional content | Bhajans, kirtans, gurbani, namaz times, hymns per the elder's faith. | Later | Added |
| DB-048 | Life-story recorder | Elder narrates memories, saved as audio for grandchildren. | Later | Added |
| DB-049 | Voice-based cognitive screening | Periodic recall/orientation tasks; flags change to family and doctor without diagnosing. | Later | Added |
| DB-050 | Adaptive memory games | Difficulty adjusts over time. | Later | Added |
| DB-051 | Peer community (satsang rooms) | Moderated voice-based group chats by area or interest. | Scale | Added |
| DB-052 | Grandchild connection | Kids send voice messages/drawings; app reads them aloud. | Later | Added |

## Daily Life

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-067 | Voice assistant for small tasks | Call a contact, read a message, set alarm, find bus/train, pay utility bill. | Later | Added |
| DB-068 | Helpline directory | Elder helpline 14567, ambulance, police, local services (editable). | Next | Added |
| DB-069 | Government scheme finder | Ayushman Bharat, pensions, concessions; eligibility and documents. | Later | Added |
| DB-070 | Document organiser | Aadhaar, PAN, insurance, pension papers with expiry reminders. | Later | Added |
| DB-071 | Insurance helper | Renewal dates and claim steps. | Later | Added |
| DB-072 | Digital literacy coach | Short lessons: video call, reading a bank SMS safely. | Later | Added |
| DB-073 | Newspaper read-aloud | Local-language headlines and 'today in history'. | Later | Added |

## Platform

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-074 | Offline mode | Reminders and basic voice work with poor connectivity. | Next | Added |
| DB-075 | Dialect and accent support | Test with real elders (Telangana, Vidarbha, Bhojpuri belts). | Next | Added |
| DB-076 | Low-end phone optimization | Light on RAM and data. | Next | Added |
| DB-077 | Hearing and vision adaptations | Captions, high contrast, adjustable speed, vibration + flash alerts. | MVP | Added |
| DB-078 | Smart speaker and wearable support | Alexa, Google Nest, basic smartwatch. | Scale | Added |
| DB-079 | Feature phone / IVR as primary channel | For elders without smartphones. | Next | Added |
| DB-080 | Caregiver-assisted setup | Child configures remotely; elder approves every sharing setting by voice. | Next | Added |

## Privacy & Trust

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-081 | ★ Plain-language consent log | 'Who saw what, and when?' answered by voice. | MVP | Added |
| DB-082 | Easy revoke | 'Stop sharing my mood with my son' in one sentence. | MVP | Added |
| DB-083 | Temporary sharing | E.g. share reports with the doctor for 7 days. | Next | Added |
| DB-084 | Nominee / incapacity handling | Auditable process with doctor or legal guardian if elder cannot consent. | Later | Added |
| DB-085 | Data export and delete | DPDP Act 2023 compliance. | Next | Added |
| DB-086 | Security baseline | Encryption, OTP login, audit trail, Indian cloud region, row-level security. | MVP | Original doc |

## Business

| ID | Feature | Description | Phase | Source |
|---|---|---|---|---|
| DB-087 | B2B2C partnerships | Hospitals, insurers, pharmacies, old-age homes, corporate benefits. | Scale | Added |
| DB-088 | Community health worker mode | ASHA/ANM check-ins in rural areas, with consent. | Scale | Added |
| DB-089 | Anonymous aggregate insights | De-identified population trends for NGOs/government. | Scale | Added |
| DB-090 | Tiered pricing | Free basic tier; paid family and care-team features. | Scale | Added |
