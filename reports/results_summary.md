# Results Summary (auto-generated)

| Test | Statistic | p-value | Conclusion |
|---|---|---|---|
| A) Mann-Whitney U: discounted vs non-discounted total_reviews | U=1354.0 (n=36 vs 64), rank-biserial r=0.175 | 0.0739 | Fail to reject H0: no significant evidence discounted games have more reviews |
| B) Spearman: playtime_hours vs recommended | rho=0.287, point-biserial r=0.205 | 6.96e-30 | Reject H0: playtime is positively associated with recommendation |
| C) Chi-square independence: price_tier vs review_summary | chi2=8.75, dof=12, Cramer's V=0.177 | 0.724 | Fail to reject H0: price tier and review summary appear independent (caution: 55% of cells have expected count < 5) |

## Anomaly detection (IQR, k=1.5)

- **Price:** fence $-23.76 to $66.24; 0 outlier games (0.0%), max $59.99.
- **Playtime:** fence -24.5 to 53.9 h; 121 outlier reviews (8.1%), max 207 h vs median 10.8 h and 99th percentile 130.1 h.
- **Dataset size after cleaning:** 100 games, 1500 reviews.
