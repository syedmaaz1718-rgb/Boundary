# Boundary chase model

This is a research portfolio workbench, not a live score service or a betting tool.

## Data and split

Cricsheet IPL JSON snapshot, fetched 8 October 2026. 1,243 matches, 142,303 second-innings delivery records. 1,185 matches have standard completed chases eligible for inference. DLS/adjusted targets, shortened matches, super overs, ties/no-results and missing chases are excluded from inference, not from the archive.

Whole matches are separated by date:
- Training 2008-2023: 977 matches, 113,865 pre-delivery states.
- Logistic calibration 2024: 70 matches, 8,108 states.
- Untouched test 2025-2026: 138 matches, 15,914 states.

The model is histogram gradient boosting with 130 iterations. It uses runs needed, legal balls left, wickets left, target, required run rate, current run rate, run pressure and wicket pressure. No player identity, final winner, eventual innings total, venue or team ID is an inference feature. Terminal states use cricket-rule boundaries rather than a learned guess.

## Measured holdout results

AUC 0.855966, Brier 0.166509, log loss 0.547481, state-weighted accuracy 0.777303. Constant training-prevalence baseline: AUC 0.5, Brier 0.247771, log loss 0.688686. These were computed, not fabricated. Full machine-readable results and calibration bins are in models/evaluation.json.

Ball states in one match are correlated. Metrics are state-weighted and cannot be treated as thousands of independent match results. No confidence interval, significance, or production accuracy claim is made. Early-, mid- and late-innings quality is not independently validated in this version.

## Important limitations

Calibration drift is material. In the 0-10% holdout bin, average predicted probability is 2.52% but observed wins are 15.28%. In the 90-100% bin, predicted mean is 96.71% while observed wins are 90.51%. The UI exposes these bins. Individual estimates can be overconfident and should not be read as trustworthy odds.

All archived curves are computed with the same training-period model. Curves for training years are in-sample. Only 2025-2026 metrics are untouched holdout metrics. Extreme hypothetical targets/states can lie outside the training distribution. The model is not constrained to be monotonic, so a counterfactual may behave unexpectedly or stay unchanged in a tree leaf.

## Player impact

Impact is a sum of changes in model-estimated win probability (percentage points) across covered chase deliveries. It is an associative attribution score, not causal contribution or player talent. Batter credit excludes extra deliveries and dismissals of a non-striker. Bowling credit excludes extra deliveries and non-bowler dismissals (run-out, retired hurt/out, obstruction). This is a simplified credit assignment: dot-ball time pressure, context, fielding and partner effects are not causally separated. Totals are volume-sensitive. Players with no covered-chase events can have zero impact. Scorecard totals cover all innings, while impact covers only eligible chases.

## Sources

- https://cricsheet.org/downloads/
- https://cricsheet.org/downloads/ipl_json.zip
- https://cricsheet.org/format/json/

Rebuild: python scripts/bootstrap.py. It downloads a new archive, recomputes scores, retrains and rewrites the database/model/report. This is explicit, not a background refresh.
