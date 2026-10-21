# Results Summary (auto-generated)

| Test | Statistic | p-value | Conclusion |
|---|---|---|---|
| A) Mann-Whitney U: discounted vs non-discounted total_reviews | U=247.0 (n=16 vs 34), rank-biserial r=-0.092 | 0.702 | Fail to reject H0: no significant evidence discounted games have more reviews |
| B) Spearman: playtime_hours vs recommended | rho=0.002, point-biserial r=-0.003 | 0.957 | Fail to reject H0: no significant monotonic association |
| C) Chi-square independence: price_tier vs review_summary | chi2=2.91, dof=6, Cramer's V=0.182 | 0.821 | Fail to reject H0: price tier and review summary appear independent (caution: 83% of cells have expected count < 5) |

## Anomaly detection (IQR, k=1.5)

- **Price:** fence $-71.23 to $118.72; 0 outlier games (0.0%), max $69.99.
- **Playtime:** fence -185.2 to 330.7 h; 135 outlier reviews (14.2%), max 11,092 h vs median 32.2 h and 99th percentile 3540.8 h.
- **Dataset size after cleaning:** 50 games, 948 reviews.
