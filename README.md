https://boundary-4y05.onrender.com
# Boundary

A 12-page cricket analytics research application with a real Flask backend, SQLite database, trained chase model, source-backed scorecards and the approved graphite/violet UI. No API key required. The ZIP includes the database and trained model, so you do not need to download the Cricsheet archive just to run it.

## Start locally

Python 3.10 or 3.11 recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000 . This is a backend application: do not double-click index.html or deploy it as a static-only Netlify site.

## Twelve pages

1. Match explorer: actual match/season selector, score state, probability curve, delivery ledger, CSV export.
2. Ball-by-ball replay: play/pause, previous/next event, timeline scrubber, speed control.
3. What-if lab: custom score/target/wickets/balls, real inference, dot/single/four/six/wicket comparisons, scenario saving.
4. Player impact: season filter, search, sorting, batting/bowling attribution alongside real scorecard totals.
5. Player profile: appearances, runs/strike rate/wickets, seasonal totals and match history.
6. Team analytics: result distribution, scoring, coverage and match links.
7. Venue analytics: venue-level scores/results and match links.
8. Season review: seasonal results, mean first-innings score and archive coverage.
9. Head-to-head: actual team-pair results and source-backed match history.
10. Scenario notebook: database-backed save/reopen/delete, isolated by signed anonymous browser session.
11. Model evaluation: computed temporal holdout metrics, baseline, reliability bins and model scope.
12. Data coverage: source links, SHA-256 manifest, exclusions and scoring rules.

Bright living icons, slow field illumination, cinematic violet workspace lighting and iris-open page transitions respect prefers-reduced-motion. All 12 pages are reachable from the compact icon rail and in-context links. Page changes use the centered iris reveal and respect reduced-motion settings. The icon rail stays fixed on desktop and becomes a horizontally scrollable, touch-friendly bottom rail on mobile.

## Honest scope

Historical archive and replay, NOT a real-time IPL feed. Custom state inference works immediately, but ongoing live-match events must be entered manually into the what-if lab. No paid sports provider is connected.

The model is research-grade and has calibration drift. See docs/MODEL_CARD.md. Player impact is associative probability-change attribution, not causal player value. Historical team/venue names are not merged. Some same-state counterfactuals produce unchanged tree-model estimates.

Notebook is isolated by a signed browser-session cookie, not login accounts. Set SECRET_KEY to a persistent random value before deployment or sessions will be lost on restart. Clearing cookies loses notebook access. This is not a production multi-user authenticated workspace. No seeded notebook/test users ship.

## Tests and rebuild

```bash
python -m pytest -q
# Optional: refresh public Cricsheet snapshot, rebuild SQLite, train and evaluate:
python scripts/bootstrap.py
```

The included model is a local trusted joblib artifact. Never replace it with an untrusted pickle/joblib download. Bootstrap rewrites the analytics database; export or back up your notebook before rebuilding.

## Deploy

Use Python hosting (Render, Railway, a VM, etc.) (a free instance works for a demo; saved scenarios reset on restart, see DEPLOY.md). Install requirements and start:

```bash
gunicorn --workers 1 --threads 2 --bind 0.0.0.0:$PORT app:app
```

Set a long random SECRET_KEY, COOKIE_SECURE=1 behind HTTPS, OPENBLAS_NUM_THREADS=2 and OMP_NUM_THREADS=2. Keep the included data/ and models/ folders. Saved notebooks are lost on ephemeral hosts; do not mount a disk over data/ (it would hide the shipped database). This package is not already deployed. Dockerfile is included.

Fonts use public Google Fonts, with system fallbacks. The app/data/model work locally without a paid API. Offline styling uses fallback fonts.

## Data credit

All match records originate from Cricsheet: https://cricsheet.org/downloads/ . JSON format: https://cricsheet.org/format/json/ . Original source notices are preserved in data/SOURCE-README.txt. Application source license is separate from upstream data terms; see DATA_LICENSE.md and LICENSE.
