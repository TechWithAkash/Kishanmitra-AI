# Changelog

All notable changes to KisanMitra AI are documented here.

- [2026-10-05 07:00] test(pipeline): verify English fallback when confidence is below threshold
- [2026-10-05 07:09] test(nlu): assert exact entity slot matching on pest and disease queries
- [2026-10-05 07:32] perf(translate): add LRU cache for frequent greeting and help queries
- [2026-10-05 08:49] fix(entities): prevent dhan substring false match on dhanyavad
- [2026-10-05 08:59] style(web): enhance dark mode contrast on Magic Card containers
- [2026-10-05 09:12] refactor(mandi): sort mandi market records by modal price descending
- [2026-10-05 09:31] feat(weather): add agricultural frost and heat stress advisory heuristics
- [2026-10-05 10:36] refactor(advice): prioritize exact crop match before generic symptom advice
- [2026-10-05 10:40] fix(web): preserve photo aspect ratio in composer preview thumbnail
- [2026-10-05 11:54] docs(mvp): update demo script queries and validation checklist
- [2026-10-05 12:29] perf(server): exclude internal speech prompt from JSON response payload
- [2026-10-05 12:36] fix(web): handle clipboard image paste in chat input box
- [2026-10-05 12:42] style(web): polish tooltip delays and toast notifications
- [2026-10-05 12:58] refactor(langid): add Romanized Marathi common marker vocabulary
- [2026-10-05 13:10] test(diagnosis): test unsupported crop warning message
- [2026-10-05 13:38] feat(web): support drag and drop image upload on chat window
- [2026-10-05 13:41] refactor(speech): prioritize Hindi over Urdu for ambiguous Devanagari acoustics
- [2026-10-05 14:15] docs(plan): annotate IndicBERT comparison benchmark methodology
- [2026-10-05 15:37] perf(web): lazy load camera stream until modal activation
- [2026-10-05 15:40] fix(web): sanitize empty transcript submissions in voice loop
- [2026-10-05 16:07] style(web): polish active chat item indicator in sidebar
- [2026-10-05 16:54] refactor(pipeline): format spoken summaries for text-to-speech output
- [2026-10-05 18:37] test(server): test health check endpoint whisper status
