# Architecture

Browser → Flask JSON API → SQLite archive and notebook. Local trained model is loaded once and protected by a prediction lock for threaded serving.

- frontend/index.html, style.css, app.js: 12 routes using History API; escaped source values, scrollable mobile tables, reduced-motion and iris transitions.
- app.py: read APIs, bounded integer prediction input, CSRF-protected mutation endpoints, anonymous session-isolated notebooks, CSV export.
- engine.py: shared state feature definitions, calibrated inference, terminal cricket rules.
- scripts/bootstrap.py: original archive download/hash, standard-chase filtering, scoring/attribution, temporal training/calibration/evaluation, SQLite ingestion.
- data/boundary.sqlite: source-backed matches, second-innings events, all-innings player totals, empty notebook table.
- models/chase.joblib: gradient boosting + logistic calibrator; evaluation.json: computed holdout report.

Security basics: parameterized SQL, escaped HTML data, same-origin mutation check, session CSRF token, bounded request body, cookie HttpOnly/SameSite, CSP with no external JavaScript, session owner scoping for notebook reads/deletes. SECRET_KEY must be persistent in deployment. Inline CSS is permitted by CSP to support generated visual bar widths. Third-party Google Fonts is optional and carries no match/notebook content.

Data is a snapshot. Bootstrap replaces analytics tables/model and should not run while the app is serving. Team aliases are not normalized. No real-time ingestion adapter or social/auth account layer is included.
