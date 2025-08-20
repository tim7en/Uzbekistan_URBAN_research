# COMPREHENSIVE STATISTICAL REVIEW
## Surface Urban Heat Island (SUHI) Analysis for Uzbekistan Cities
Generated: 2025-08-20 08:27:13

---

## EXECUTIVE SUMMARY
- **Dataset**: 28 observations from 14 cities
- **Time Period**: 2017-2024
- **Statistical Significance Level**: α = 0.05

## NORMALITY TESTING
Assessment of data distribution assumptions for parametric tests.

| Variable | Shapiro-Wilk | Kolmogorov-Smirnov | Normal Distribution |
|----------|--------------|-------------------|-------------------|
| SUHI | W=0.8229, p=0.0003 | D=0.2051, p=0.1645 | ✗ No |
| SUHI_Day | W=0.8730, p=0.0028 | D=0.1862, p=0.2529 | ✗ No |
| SUHI_Night | W=0.9323, p=0.0706 | D=0.1456, p=0.5447 | ✓ Yes |
| Urban_Temp_Day | W=0.9759, p=0.7445 | D=0.0674, p=0.9986 | ✓ Yes |
| Rural_Temp_Day | W=0.8787, p=0.0038 | D=0.1625, p=0.4066 | ✗ No |
| Urban_Pixels | W=0.7275, p=0.0000 | D=0.2142, p=0.1317 | ✗ No |
| Rural_Pixels | W=0.9677, p=0.5212 | D=0.1210, p=0.7624 | ✓ Yes |

## HYPOTHESIS TESTING RESULTS

### Year Comparison (2017 vs 2024)
- **Mann-Whitney U test**: U = 87.0000, p = 0.6295

### City Comparison
- **One-way ANOVA**: F = 37.6494, p = 0.0000
- **Kruskal-Wallis test**: H = 25.2266, p = 0.0216
- **Effect Size**: η² = 0.9722

### Paired Analysis (Within-City Changes)
- **Paired t-test**: t = -2.6493, p = 0.0200
- **Wilcoxon signed-rank**: W = 19.0000, p = 0.0353
- **Mean Change**: 0.551°C
- **95% CI for Change**: [0.102, 1.000]°C

## STATISTICAL POWER ANALYSIS
- **Effect Size**: 0.1912
- **Achieved Power**: 0.1018 (10.2%)
- **Required Sample Size**: 217 per group for 80% power

## OUTLIER ANALYSIS
- **Z-score outliers**: 0
- **IQR outliers**: 3
- **Modified Z-score outliers**: 2

## TEMPORAL TREND ANALYSIS
- **Slope**: 0.078688°C/year
- **Slope Significance**: p = 0.6172
- **R-squared**: 0.0097
- **Model F-test**: F = 0.2560, p = 0.6172
- **Durbin-Watson**: 1.1650
- **Heteroscedasticity test**: LM = 0.1529, p = 0.6958

## STATISTICAL INTERPRETATION
### Key Findings:

### Statistical Recommendations:
- Mixed normality results; consider both parametric and non-parametric tests
- Study is underpowered (power = 10.2%); consider increasing sample size to 217 per group
- Multiple city comparisons performed; consider Bonferroni correction for family-wise error rate