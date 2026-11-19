Machine learning in this project
Algorithms actually used
#	Algorithm	Library class	Where it is used	Settings and role
1	Logistic regression (L2-regularised)	LogisticRegression	Final model (GMP-only), the subscription fallback, all harness models A, S, B, C, D, E, and the checklist-score calibration	Probability of a positive listing. C=1, unweighted so probabilities stay interpretable (the early v1 baseline used class_weight="balanced")
2	Ridge regression	Ridge(alpha=10)	Early baselines	Predicting the gain in points. MAE 8.8 against 8.25 for using GMP directly
3	Random forest classifier	RandomForestClassifier	Early baseline (300 trees, leaf 5, balanced subsample) and the challenger check (400 trees, leaf 8)	Non-linear benchmark. AUC 0.844, no better than GMP-only
4	Random forest regressor	RandomForestRegressor	Early regression baseline (300 trees)	Gain-size baseline
5	Gradient boosting with monotonic constraints	HistGradientBoostingClassifier	Challenger check (depth 2, learning rate 0.05, 150 iterations, monotonic_cst=[1,1])	Tests whether a boosted model beats A. It does not (AUC 0.852)
6	Baselines	DummyClassifier, DummyRegressor, prior rate, GMP used as the forecast, rules “flag if GMP ≤ 0/5/10%”	Harness and early baselines	Reference points a model must beat
7	Empirical quantile intervals	pandas quantile	final_model.residual_quantiles	80% gain range from past (actual gain − GMP) by GMP bucket, conformal-style but not formal conformal prediction

Not ML models but related: fuzzy string matching (difflib.SequenceMatcher) for record linkage, and Spearman rank correlation for EDA.

Preprocessing: median imputation (SimpleImputer), standardisation (StandardScaler), log and log1p transforms, clipping outliers, and a rolling feature (mean gain of the previous 10 or 30 listings, built strictly from earlier dates).

Concepts, grouped
Area	Concepts and where they appear
Problem framing	Supervised binary classification and regression; target definition and the effect of the “flat counts as non-positive” threshold; three prediction stages (pre-close, post-close, listing-eve)
Features and data	Feature engineering (GMP as % of issue price, log subscription, momentum, Nifty and VIX context, log issue size); missing-data handling (blank, never zero, a gmp_missing flag, imputation, fallback models); outlier handling; record linkage and de-duplication; label noise and a robustness variant (clear-only labels); data validation and schema constraints; provenance
Leakage and validation design	Look-ahead leakage and stage-aware rules enforced in code; expanding-window walk-forward validation (no random shuffles); features built only from earlier dates; a test that fold training data ends before test data starts
Modelling	Regularisation; standardisation; baseline and benchmark discipline; overfitting and bias-variance (a 13-feature model lost to a 1-feature model); ablation of feature sets A to E; bagging (random forest) and boosting; monotonic constraints; class imbalance (class weights in v1 against unweighted models for calibration, imbalance-aware metrics)
Evaluation	ROC-AUC, PR-AUC for the non-positive class, accuracy against the majority-class baseline, precision/recall/F1, recall at a fixed flag rate (operating points), Brier score, log-loss, calibration (reliability curves, expected calibration error), MAE; subgroup analysis by GMP zone and year; regime change; ranking quality against thresholded decisions
Statistical inference	Paired bootstrap for model differences; block bootstrap by quarter for dependent samples; confidence intervals and “is the difference noise?” reasoning; prediction intervals and coverage checking out-of-sample; a pre-registered benchmark and primary metric
Decision-making	Probability to risk band via thresholds, validated out-of-sample; communicating uncertainty (the weak zone is stated in the app); parsimony in model selection; reporting negative results
Engineering	Reproducibility (fixed seeds, deterministic sorting, identical file hashes across runs); model persistence (joblib); unit, integration and app smoke tests; data contracts through validators; immutable IDs; version control
EDA	Spearman correlations, bucket tables, a two-way GMP by subscription heatmap, distribution and year-over-year analysis
What this project does not use

Deep learning, XGBoost or LightGBM, SHAP, clustering, PCA, hyperparameter search or a cross-validated grid (settings are fixed, not tuned), stacking, oversampling such as SMOTE, formal conformal prediction, isotonic calibration, Bayesian models, or NLP (the retrieval and embeddings work arrives in Phase 5). Don’t claim these in an evaluation.