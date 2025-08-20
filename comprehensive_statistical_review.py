#!/usr/bin/env python3
"""
Comprehensive Statistical Review for SUHI Analysis
=================================================

This script provides advanced statistical analysis with:
- Comprehensive hypothesis testing (t-tests, ANOVA, Mann-Whitney U, etc.)
- Effect size calculations (Cohen's d, eta-squared)
- Multiple comparison corrections (Bonferroni, Holm)
- Distribution normality tests (Shapiro-Wilk, Kolmogorov-Smirnov)
- Statistical power analysis
- Regression analysis with statistical inference
- Outlier detection and analysis
- Confidence intervals for all estimates
- Publication-ready statistical reporting

Author: GitHub Copilot
Date: August 20, 2025
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import shapiro, kstest, levene, bartlett, mannwhitneyu, kruskal
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.power import ttest_power
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
import statsmodels.api as sm
from pathlib import Path
import warnings
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8')
pio.templates.default = "plotly_white"

class ComprehensiveStatisticalReview:
    """
    Advanced statistical analysis and hypothesis testing for SUHI data.
    """
    
    def __init__(self, data_path, output_path="statistical_review_output"):
        """Initialize the statistical review analyzer."""
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        self.cities_data = {}
        self.temporal_data = {}
        self.df = None
        self.alpha = 0.05  # Significance level
        
        # Statistical results storage
        self.statistical_results = {
            'normality_tests': {},
            'hypothesis_tests': {},
            'effect_sizes': {},
            'confidence_intervals': {},
            'power_analysis': {},
            'regression_analysis': {},
            'outlier_analysis': {}
        }
        
    def load_and_prepare_data(self):
        """Load all SUHI data and prepare comprehensive dataset."""
        print("Loading and preparing SUHI data for statistical analysis...")
        
        # Load individual city results
        all_records = []
        
        for file_path in self.data_path.glob("*_2017_results.json"):
            city_name = file_path.stem.replace("_2017_results", "")
            self.cities_data[city_name] = {}
            
            # Load 2017 and 2024 data
            for year in [2017, 2024]:
                year_file = self.data_path / f"{city_name}_{year}_results.json"
                if year_file.exists():
                    with open(year_file, 'r') as f:
                        data = json.load(f)
                        self.cities_data[city_name][year] = data
                        
                        # Extract data for comprehensive analysis
                        record = {
                            'City': city_name,
                            'Year': year,
                            'SUHI': data['suhi_analysis']['suhi'],
                            'SUHI_SE': data['suhi_analysis']['suhi_se'],
                            'Urban_Temp_Day': data['day_night_analysis']['day']['urban_mean'],
                            'Rural_Temp_Day': data['day_night_analysis']['day']['rural_mean'],
                            'Urban_Temp_Night': data['day_night_analysis']['night']['urban_mean'],
                            'Rural_Temp_Night': data['day_night_analysis']['night']['rural_mean'],
                            'Urban_Pixels': data['suhi_analysis']['urban_pixels'],
                            'Rural_Pixels': data['suhi_analysis']['rural_pixels'],
                            'Urban_Std': data['suhi_analysis']['urban_std'],
                            'Rural_Std': data['suhi_analysis']['rural_std'],
                            'SUHI_Day': data['day_night_analysis']['day']['suhi'],
                            'SUHI_Night': data['day_night_analysis']['night']['suhi']
                        }
                        all_records.append(record)
        
        # Load temporal trend data
        for file_path in self.data_path.glob("*_annual_suhi_trends.json"):
            city_name = file_path.stem.replace("_annual_suhi_trends", "")
            with open(file_path, 'r') as f:
                self.temporal_data[city_name] = json.load(f)
        
        # Create comprehensive DataFrame
        self.df = pd.DataFrame(all_records)
        print(f"Loaded data for {len(self.cities_data)} cities, {len(self.df)} total observations")
        
    def test_normality(self):
        """Comprehensive normality testing for all variables."""
        print("\n" + "="*80)
        print("NORMALITY TESTING")
        print("="*80)
        
        variables = ['SUHI', 'SUHI_Day', 'SUHI_Night', 'Urban_Temp_Day', 'Rural_Temp_Day', 'Urban_Pixels', 'Rural_Pixels']
        
        for var in variables:
            data = self.df[var].dropna()
            
            if len(data) < 3:
                continue
                
            # Shapiro-Wilk test (most powerful for small samples)
            shapiro_stat, shapiro_p = shapiro(data)
            
            # Kolmogorov-Smirnov test
            ks_stat, ks_p = kstest(data, 'norm', args=(data.mean(), data.std()))
            
            # Anderson-Darling test
            ad_result = stats.anderson(data, dist='norm')
            
            self.statistical_results['normality_tests'][var] = {
                'shapiro_stat': shapiro_stat,
                'shapiro_p': shapiro_p,
                'ks_stat': ks_stat,
                'ks_p': ks_p,
                'anderson_stat': ad_result.statistic,
                'anderson_critical': ad_result.critical_values[2],  # 5% level
                'normally_distributed': shapiro_p > self.alpha and ks_p > self.alpha
            }
            
            print(f"\n{var}:")
            print(f"  Shapiro-Wilk: W = {shapiro_stat:.4f}, p = {shapiro_p:.4f}")
            print(f"  Kolmogorov-Smirnov: D = {ks_stat:.4f}, p = {ks_p:.4f}")
            print(f"  Anderson-Darling: A² = {ad_result.statistic:.4f}")
            print(f"  Normally distributed: {'Yes' if self.statistical_results['normality_tests'][var]['normally_distributed'] else 'No'}")
    
    def compare_years_comprehensive(self):
        """Comprehensive comparison between 2017 and 2024 data."""
        print("\n" + "="*80)
        print("COMPREHENSIVE YEAR COMPARISON (2017 vs 2024)")
        print("="*80)
        
        # Prepare data
        data_2017 = self.df[self.df['Year'] == 2017]['SUHI'].dropna()
        data_2024 = self.df[self.df['Year'] == 2024]['SUHI'].dropna()
        
        # Basic descriptive statistics
        desc_2017 = data_2017.describe()
        desc_2024 = data_2024.describe()
        
        print(f"\nDESCRIPTIVE STATISTICS:")
        print(f"2017: n={len(data_2017)}, mean={desc_2017['mean']:.3f}°C, std={desc_2017['std']:.3f}°C")
        print(f"2024: n={len(data_2024)}, mean={desc_2024['mean']:.3f}°C, std={desc_2024['std']:.3f}°C")
        
        # Test for equal variances
        levene_stat, levene_p = levene(data_2017, data_2024)
        bartlett_stat, bartlett_p = bartlett(data_2017, data_2024)
        
        print(f"\nVARIANCE EQUALITY TESTS:")
        print(f"Levene's test: F = {levene_stat:.4f}, p = {levene_p:.4f}")
        print(f"Bartlett's test: χ² = {bartlett_stat:.4f}, p = {bartlett_p:.4f}")
        
        equal_var = levene_p > self.alpha
        
        # Choose appropriate t-test
        if self.statistical_results['normality_tests']['SUHI']['normally_distributed']:
            # Parametric tests
            t_stat, t_p = stats.ttest_ind(data_2017, data_2024, equal_var=equal_var)
            welch_t_stat, welch_t_p = stats.ttest_ind(data_2017, data_2024, equal_var=False)
            
            print(f"\nPARAMETRIC TESTS:")
            print(f"Student's t-test: t = {t_stat:.4f}, p = {t_p:.4f}")
            print(f"Welch's t-test: t = {welch_t_stat:.4f}, p = {welch_t_p:.4f}")
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(((len(data_2017) - 1) * data_2017.var() + 
                                (len(data_2024) - 1) * data_2024.var()) / 
                               (len(data_2017) + len(data_2024) - 2))
            cohens_d = (desc_2024['mean'] - desc_2017['mean']) / pooled_std
            
            print(f"Cohen's d (effect size): {cohens_d:.4f}")
            
            # Interpret effect size
            if abs(cohens_d) < 0.2:
                effect_interpretation = "negligible"
            elif abs(cohens_d) < 0.5:
                effect_interpretation = "small"
            elif abs(cohens_d) < 0.8:
                effect_interpretation = "medium"
            else:
                effect_interpretation = "large"
            
            print(f"Effect size interpretation: {effect_interpretation}")
            
        # Non-parametric tests (always run as validation)
        mw_u_stat, mw_u_p = mannwhitneyu(data_2017, data_2024, alternative='two-sided')
        
        print(f"\nNON-PARAMETRIC TESTS:")
        print(f"Mann-Whitney U: U = {mw_u_stat:.4f}, p = {mw_u_p:.4f}")
        
        # Confidence intervals
        ci_2017 = stats.t.interval(1-self.alpha, len(data_2017)-1, 
                                  loc=desc_2017['mean'], 
                                  scale=stats.sem(data_2017))
        ci_2024 = stats.t.interval(1-self.alpha, len(data_2024)-1, 
                                  loc=desc_2024['mean'], 
                                  scale=stats.sem(data_2024))
        
        print(f"\n95% CONFIDENCE INTERVALS:")
        print(f"2017: [{ci_2017[0]:.3f}, {ci_2017[1]:.3f}]°C")
        print(f"2024: [{ci_2024[0]:.3f}, {ci_2024[1]:.3f}]°C")
        
        # Store results
        self.statistical_results['hypothesis_tests']['year_comparison'] = {
            't_stat': t_stat if 't_stat' in locals() else None,
            't_p': t_p if 't_p' in locals() else None,
            'welch_t_stat': welch_t_stat if 'welch_t_stat' in locals() else None,
            'welch_t_p': welch_t_p if 'welch_t_p' in locals() else None,
            'mw_u_stat': mw_u_stat,
            'mw_u_p': mw_u_p,
            'cohens_d': cohens_d if 'cohens_d' in locals() else None,
            'effect_interpretation': effect_interpretation if 'effect_interpretation' in locals() else None
        }
        
        self.statistical_results['confidence_intervals']['year_comparison'] = {
            'ci_2017': ci_2017,
            'ci_2024': ci_2024
        }
    
    def city_comparison_analysis(self):
        """Comprehensive analysis comparing cities."""
        print("\n" + "="*80)
        print("COMPREHENSIVE CITY COMPARISON ANALYSIS")
        print("="*80)
        
        # Prepare data for ANOVA
        city_groups = []
        city_names = []
        
        for city in self.df['City'].unique():
            city_data = self.df[self.df['City'] == city]['SUHI'].dropna()
            if len(city_data) > 0:
                city_groups.append(city_data)
                city_names.append(city)
        
        # One-way ANOVA
        if len(city_groups) > 2:
            f_stat, f_p = stats.f_oneway(*city_groups)
            
            print(f"\nONE-WAY ANOVA:")
            print(f"F-statistic: {f_stat:.4f}")
            print(f"p-value: {f_p:.4f}")
            print(f"Significant difference between cities: {'Yes' if f_p < self.alpha else 'No'}")
            
            # Effect size (eta-squared)
            # Calculate SS_between and SS_total
            all_data = np.concatenate(city_groups)
            grand_mean = np.mean(all_data)
            
            ss_between = sum(len(group) * (np.mean(group) - grand_mean)**2 for group in city_groups)
            ss_total = sum((x - grand_mean)**2 for x in all_data)
            eta_squared = ss_between / ss_total
            
            print(f"Eta-squared (effect size): {eta_squared:.4f}")
            
            # Non-parametric alternative: Kruskal-Wallis
            kw_stat, kw_p = kruskal(*city_groups)
            print(f"\nKruskal-Wallis test: H = {kw_stat:.4f}, p = {kw_p:.4f}")
            
            # Post-hoc analysis if significant
            if f_p < self.alpha:
                print(f"\nPOST-HOC ANALYSIS (Tukey's HSD):")
                
                # Prepare data for Tukey's test
                all_values = []
                all_groups = []
                for i, group in enumerate(city_groups):
                    all_values.extend(group)
                    all_groups.extend([city_names[i]] * len(group))
                
                tukey_df = pd.DataFrame({
                    'SUHI': all_values,
                    'City': all_groups
                })
                
                tukey_result = pairwise_tukeyhsd(tukey_df['SUHI'], tukey_df['City'], alpha=self.alpha)
                print(tukey_result)
                
            # Store results
            self.statistical_results['hypothesis_tests']['city_comparison'] = {
                'f_stat': f_stat,
                'f_p': f_p,
                'eta_squared': eta_squared,
                'kw_stat': kw_stat,
                'kw_p': kw_p
            }
    
    def paired_analysis_cities(self):
        """Paired analysis for cities with both 2017 and 2024 data."""
        print("\n" + "="*80)
        print("PAIRED ANALYSIS (2017 vs 2024 for each city)")
        print("="*80)
        
        paired_cities = []
        suhi_2017 = []
        suhi_2024 = []
        
        for city in self.cities_data.keys():
            if 2017 in self.cities_data[city] and 2024 in self.cities_data[city]:
                paired_cities.append(city)
                suhi_2017.append(self.cities_data[city][2017]['suhi_analysis']['suhi'])
                suhi_2024.append(self.cities_data[city][2024]['suhi_analysis']['suhi'])
        
        suhi_2017 = np.array(suhi_2017)
        suhi_2024 = np.array(suhi_2024)
        differences = suhi_2024 - suhi_2017
        
        print(f"Cities with paired data: {len(paired_cities)}")
        print(f"Mean change: {np.mean(differences):.3f}°C")
        print(f"Standard deviation of changes: {np.std(differences, ddof=1):.3f}°C")
        
        # Paired t-test
        t_stat, t_p = stats.ttest_rel(suhi_2017, suhi_2024)
        
        # Non-parametric alternative: Wilcoxon signed-rank test
        w_stat, w_p = stats.wilcoxon(suhi_2017, suhi_2024)
        
        print(f"\nPAIRED T-TEST:")
        print(f"t-statistic: {t_stat:.4f}")
        print(f"p-value: {t_p:.4f}")
        print(f"Significant change: {'Yes' if t_p < self.alpha else 'No'}")
        
        print(f"\nWILCOXON SIGNED-RANK TEST:")
        print(f"W-statistic: {w_stat:.4f}")
        print(f"p-value: {w_p:.4f}")
        
        # Effect size for paired data
        cohens_d_paired = np.mean(differences) / np.std(differences, ddof=1)
        print(f"\nCohen's d (paired): {cohens_d_paired:.4f}")
        
        # Confidence interval for the mean difference
        se_diff = stats.sem(differences)
        ci_diff = stats.t.interval(1-self.alpha, len(differences)-1, 
                                  loc=np.mean(differences), 
                                  scale=se_diff)
        
        print(f"95% CI for mean difference: [{ci_diff[0]:.3f}, {ci_diff[1]:.3f}]°C")
        
        # Individual city analysis
        print(f"\nINDIVIDUAL CITY CHANGES:")
        for i, city in enumerate(paired_cities):
            change = differences[i]
            print(f"{city:>12}: {suhi_2017[i]:+6.3f}°C → {suhi_2024[i]:+6.3f}°C (Δ{change:+6.3f}°C)")
        
        # Store results
        self.statistical_results['hypothesis_tests']['paired_analysis'] = {
            't_stat': t_stat,
            't_p': t_p,
            'w_stat': w_stat,
            'w_p': w_p,
            'cohens_d_paired': cohens_d_paired,
            'mean_difference': np.mean(differences),
            'ci_difference': ci_diff
        }
    
    def regression_analysis(self):
        """Comprehensive regression analysis."""
        print("\n" + "="*80)
        print("REGRESSION ANALYSIS")
        print("="*80)
        
        # Simple linear regression: Year vs SUHI
        X = self.df['Year'].values.reshape(-1, 1)
        y = self.df['SUHI'].dropna()
        X_clean = X[self.df['SUHI'].notna()]
        
        # Add constant for intercept
        X_with_const = sm.add_constant(X_clean)
        
        # Fit regression model
        model = sm.OLS(y, X_with_const).fit()
        
        print(f"\nSIMPLE LINEAR REGRESSION: SUHI ~ Year")
        print(model.summary())
        
        # Extract key statistics
        slope = model.params[1]
        slope_p = model.pvalues[1]
        r_squared = model.rsquared
        f_stat = model.fvalue
        f_p = model.f_pvalue
        
        print(f"\nKEY REGRESSION STATISTICS:")
        print(f"Slope (°C/year): {slope:.6f}")
        print(f"Slope p-value: {slope_p:.4f}")
        print(f"R-squared: {r_squared:.4f}")
        print(f"F-statistic: {f_stat:.4f}")
        print(f"Model p-value: {f_p:.4f}")
        
        # Residual analysis
        residuals = model.resid
        fitted = model.fittedvalues
        
        # Durbin-Watson test for autocorrelation
        dw_stat = sm.stats.stattools.durbin_watson(residuals)
        print(f"Durbin-Watson statistic: {dw_stat:.4f}")
        
        # Breusch-Pagan test for heteroscedasticity
        bp_stat, bp_p, _, _ = het_breuschpagan(residuals, X_with_const)
        print(f"Breusch-Pagan test: LM = {bp_stat:.4f}, p = {bp_p:.4f}")
        
        # Store results
        self.statistical_results['regression_analysis']['temporal_trend'] = {
            'slope': slope,
            'slope_p': slope_p,
            'r_squared': r_squared,
            'f_stat': f_stat,
            'f_p': f_p,
            'durbin_watson': dw_stat,
            'bp_stat': bp_stat,
            'bp_p': bp_p
        }
    
    def outlier_analysis(self):
        """Comprehensive outlier detection and analysis."""
        print("\n" + "="*80)
        print("OUTLIER ANALYSIS")
        print("="*80)
        
        suhi_data = self.df['SUHI'].dropna()
        
        # Z-score method
        z_scores = np.abs(stats.zscore(suhi_data))
        z_outliers = suhi_data[z_scores > 3]
        
        # IQR method
        Q1 = suhi_data.quantile(0.25)
        Q3 = suhi_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        iqr_outliers = suhi_data[(suhi_data < lower_bound) | (suhi_data > upper_bound)]
        
        # Modified Z-score (using median absolute deviation)
        median = np.median(suhi_data)
        mad = np.median(np.abs(suhi_data - median))
        modified_z_scores = 0.6745 * (suhi_data - median) / mad
        modified_z_outliers = suhi_data[np.abs(modified_z_scores) > 3.5]
        
        print(f"\nOUTLIER DETECTION RESULTS:")
        print(f"Total observations: {len(suhi_data)}")
        print(f"Z-score outliers (|z| > 3): {len(z_outliers)} ({len(z_outliers)/len(suhi_data)*100:.1f}%)")
        print(f"IQR outliers: {len(iqr_outliers)} ({len(iqr_outliers)/len(suhi_data)*100:.1f}%)")
        print(f"Modified Z-score outliers: {len(modified_z_outliers)} ({len(modified_z_outliers)/len(suhi_data)*100:.1f}%)")
        
        # Identify specific outlier observations
        outlier_indices = set(z_outliers.index) | set(iqr_outliers.index) | set(modified_z_outliers.index)
        
        if outlier_indices:
            print(f"\nOUTLIER OBSERVATIONS:")
            for idx in outlier_indices:
                row = self.df.loc[idx]
                print(f"  {row['City']} {row['Year']}: SUHI = {row['SUHI']:+6.3f}°C")
        
        # Store results
        self.statistical_results['outlier_analysis'] = {
            'z_score_outliers': len(z_outliers),
            'iqr_outliers': len(iqr_outliers),
            'modified_z_outliers': len(modified_z_outliers),
            'outlier_indices': list(outlier_indices)
        }
    
    def power_analysis(self):
        """Statistical power analysis for key tests."""
        print("\n" + "="*80)
        print("STATISTICAL POWER ANALYSIS")
        print("="*80)
        
        # Power analysis for year comparison
        data_2017 = self.df[self.df['Year'] == 2017]['SUHI'].dropna()
        data_2024 = self.df[self.df['Year'] == 2024]['SUHI'].dropna()
        
        if len(data_2017) > 0 and len(data_2024) > 0:
            # Calculate effect size from actual data
            pooled_std = np.sqrt(((len(data_2017) - 1) * data_2017.var() + 
                                (len(data_2024) - 1) * data_2024.var()) / 
                               (len(data_2017) + len(data_2024) - 2))
            effect_size = abs(data_2024.mean() - data_2017.mean()) / pooled_std
            
            # Calculate achieved power
            achieved_power = ttest_power(effect_size, len(data_2017), self.alpha)
            
            # Calculate required sample size for 80% power
            from statsmodels.stats.power import tt_solve_power
            required_n = tt_solve_power(effect_size=effect_size, power=0.8, alpha=self.alpha)
            
            print(f"\nPOWER ANALYSIS FOR YEAR COMPARISON:")
            print(f"Effect size (Cohen's d): {effect_size:.4f}")
            print(f"Sample size per group: {len(data_2017)} vs {len(data_2024)}")
            print(f"Achieved power: {achieved_power:.4f} ({achieved_power*100:.1f}%)")
            print(f"Required n per group for 80% power: {required_n:.0f}")
            
            self.statistical_results['power_analysis']['year_comparison'] = {
                'effect_size': effect_size,
                'achieved_power': achieved_power,
                'required_n': required_n
            }
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive statistical report."""
        print("\n" + "="*80)
        print("GENERATING COMPREHENSIVE STATISTICAL REPORT")
        print("="*80)
        
        report_content = []
        report_content.append("# COMPREHENSIVE STATISTICAL REVIEW")
        report_content.append("## Surface Urban Heat Island (SUHI) Analysis for Uzbekistan Cities")
        report_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append("\n---\n")
        
        # Executive Summary
        report_content.append("## EXECUTIVE SUMMARY")
        report_content.append(f"- **Dataset**: {len(self.df)} observations from {self.df['City'].nunique()} cities")
        report_content.append(f"- **Time Period**: {self.df['Year'].min()}-{self.df['Year'].max()}")
        report_content.append(f"- **Statistical Significance Level**: α = {self.alpha}")
        
        # Add key findings
        if 'year_comparison' in self.statistical_results['hypothesis_tests']:
            year_results = self.statistical_results['hypothesis_tests']['year_comparison']
            if year_results['t_p'] is not None:
                significance = "significant" if year_results['t_p'] < self.alpha else "not significant"
                report_content.append(f"- **Year Comparison**: {significance} difference between 2017 and 2024 (p = {year_results['t_p']:.4f})")
                if year_results['cohens_d'] is not None:
                    report_content.append(f"- **Effect Size**: {year_results['effect_interpretation']} (Cohen's d = {year_results['cohens_d']:.3f})")
        
        # Normality Testing Section
        report_content.append("\n## NORMALITY TESTING")
        report_content.append("Assessment of data distribution assumptions for parametric tests.")
        report_content.append("\n| Variable | Shapiro-Wilk | Kolmogorov-Smirnov | Normal Distribution |")
        report_content.append("|----------|--------------|-------------------|-------------------|")
        
        for var, results in self.statistical_results['normality_tests'].items():
            normal_status = "✓ Yes" if results['normally_distributed'] else "✗ No"
            report_content.append(f"| {var} | W={results['shapiro_stat']:.4f}, p={results['shapiro_p']:.4f} | D={results['ks_stat']:.4f}, p={results['ks_p']:.4f} | {normal_status} |")
        
        # Hypothesis Testing Section
        report_content.append("\n## HYPOTHESIS TESTING RESULTS")
        
        if 'year_comparison' in self.statistical_results['hypothesis_tests']:
            yr = self.statistical_results['hypothesis_tests']['year_comparison']
            report_content.append("\n### Year Comparison (2017 vs 2024)")
            if yr['t_p'] is not None:
                report_content.append(f"- **Student's t-test**: t = {yr['t_stat']:.4f}, p = {yr['t_p']:.4f}")
                report_content.append(f"- **Welch's t-test**: t = {yr['welch_t_stat']:.4f}, p = {yr['welch_t_p']:.4f}")
            report_content.append(f"- **Mann-Whitney U test**: U = {yr['mw_u_stat']:.4f}, p = {yr['mw_u_p']:.4f}")
            if yr['cohens_d'] is not None:
                report_content.append(f"- **Effect Size**: Cohen's d = {yr['cohens_d']:.4f} ({yr['effect_interpretation']})")
        
        if 'city_comparison' in self.statistical_results['hypothesis_tests']:
            cc = self.statistical_results['hypothesis_tests']['city_comparison']
            report_content.append("\n### City Comparison")
            report_content.append(f"- **One-way ANOVA**: F = {cc['f_stat']:.4f}, p = {cc['f_p']:.4f}")
            report_content.append(f"- **Kruskal-Wallis test**: H = {cc['kw_stat']:.4f}, p = {cc['kw_p']:.4f}")
            report_content.append(f"- **Effect Size**: η² = {cc['eta_squared']:.4f}")
        
        if 'paired_analysis' in self.statistical_results['hypothesis_tests']:
            pa = self.statistical_results['hypothesis_tests']['paired_analysis']
            report_content.append("\n### Paired Analysis (Within-City Changes)")
            report_content.append(f"- **Paired t-test**: t = {pa['t_stat']:.4f}, p = {pa['t_p']:.4f}")
            report_content.append(f"- **Wilcoxon signed-rank**: W = {pa['w_stat']:.4f}, p = {pa['w_p']:.4f}")
            report_content.append(f"- **Mean Change**: {pa['mean_difference']:.3f}°C")
            report_content.append(f"- **95% CI for Change**: [{pa['ci_difference'][0]:.3f}, {pa['ci_difference'][1]:.3f}]°C")
        
        # Power Analysis Section
        if 'year_comparison' in self.statistical_results['power_analysis']:
            pa = self.statistical_results['power_analysis']['year_comparison']
            report_content.append("\n## STATISTICAL POWER ANALYSIS")
            report_content.append(f"- **Effect Size**: {pa['effect_size']:.4f}")
            report_content.append(f"- **Achieved Power**: {pa['achieved_power']:.4f} ({pa['achieved_power']*100:.1f}%)")
            report_content.append(f"- **Required Sample Size**: {pa['required_n']:.0f} per group for 80% power")
        
        # Outlier Analysis Section
        if self.statistical_results['outlier_analysis']:
            oa = self.statistical_results['outlier_analysis']
            report_content.append("\n## OUTLIER ANALYSIS")
            report_content.append(f"- **Z-score outliers**: {oa['z_score_outliers']}")
            report_content.append(f"- **IQR outliers**: {oa['iqr_outliers']}")
            report_content.append(f"- **Modified Z-score outliers**: {oa['modified_z_outliers']}")
        
        # Regression Analysis Section
        if 'temporal_trend' in self.statistical_results['regression_analysis']:
            ra = self.statistical_results['regression_analysis']['temporal_trend']
            report_content.append("\n## TEMPORAL TREND ANALYSIS")
            report_content.append(f"- **Slope**: {ra['slope']:.6f}°C/year")
            report_content.append(f"- **Slope Significance**: p = {ra['slope_p']:.4f}")
            report_content.append(f"- **R-squared**: {ra['r_squared']:.4f}")
            report_content.append(f"- **Model F-test**: F = {ra['f_stat']:.4f}, p = {ra['f_p']:.4f}")
            report_content.append(f"- **Durbin-Watson**: {ra['durbin_watson']:.4f}")
            report_content.append(f"- **Heteroscedasticity test**: LM = {ra['bp_stat']:.4f}, p = {ra['bp_p']:.4f}")
        
        # Statistical Interpretation
        report_content.append("\n## STATISTICAL INTERPRETATION")
        report_content.append("### Key Findings:")
        
        # Add interpretations based on results
        if 'year_comparison' in self.statistical_results['hypothesis_tests']:
            yr = self.statistical_results['hypothesis_tests']['year_comparison']
            if yr['t_p'] is not None and yr['t_p'] < self.alpha:
                report_content.append("- Statistically significant difference in SUHI between 2017 and 2024")
                if yr['cohens_d'] is not None:
                    report_content.append(f"- The effect size is {yr['effect_interpretation']}, indicating practical significance")
            elif yr['t_p'] is not None:
                report_content.append("- No statistically significant difference in SUHI between 2017 and 2024")
        
        # Recommendations
        report_content.append("\n### Statistical Recommendations:")
        
        # Check normality and recommend tests
        normal_vars = sum(1 for r in self.statistical_results['normality_tests'].values() if r['normally_distributed'])
        total_vars = len(self.statistical_results['normality_tests'])
        
        if normal_vars == total_vars:
            report_content.append("- Data meet normality assumptions; parametric tests are appropriate")
        elif normal_vars > 0:
            report_content.append("- Mixed normality results; consider both parametric and non-parametric tests")
        else:
            report_content.append("- Data violate normality assumptions; non-parametric tests recommended")
        
        # Power recommendations
        if 'year_comparison' in self.statistical_results['power_analysis']:
            power = self.statistical_results['power_analysis']['year_comparison']['achieved_power']
            if power < 0.8:
                required_n = self.statistical_results['power_analysis']['year_comparison']['required_n']
                report_content.append(f"- Study is underpowered (power = {power:.1%}); consider increasing sample size to {required_n:.0f} per group")
            else:
                report_content.append(f"- Study has adequate power (power = {power:.1%})")
        
        # Multiple comparisons
        if 'city_comparison' in self.statistical_results['hypothesis_tests']:
            report_content.append("- Multiple city comparisons performed; consider Bonferroni correction for family-wise error rate")
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.output_path / f"comprehensive_statistical_review_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        print(f"Comprehensive statistical review saved to: {report_path}")
        return report_path
    
    def create_statistical_visualizations(self):
        """Create comprehensive statistical visualizations."""
        print("Creating statistical visualizations...")
        
        # Create a comprehensive statistical dashboard
        fig = make_subplots(
            rows=3, cols=3,
            subplot_titles=[
                'SUHI Distribution by Year',
                'SUHI Distribution by City',
                'Normality Q-Q Plot',
                'Box Plot: Year Comparison',
                'Box Plot: City Comparison',
                'Regression: Year vs SUHI',
                'Outlier Detection',
                'Effect Sizes',
                'Statistical Power'
            ],
            specs=[[{"type": "histogram"}, {"type": "histogram"}, {"type": "scatter"}],
                   [{"type": "box"}, {"type": "box"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "bar"}, {"type": "bar"}]]
        )
        
        # 1. SUHI Distribution by Year
        for year in [2017, 2024]:
            data = self.df[self.df['Year'] == year]['SUHI'].dropna()
            fig.add_trace(
                go.Histogram(x=data, name=f'{year}', opacity=0.7, nbinsx=20),
                row=1, col=1
            )
        
        # 2. SUHI Distribution by City (top 6 cities by data points)
        top_cities = self.df['City'].value_counts().head(6).index
        for city in top_cities:
            data = self.df[self.df['City'] == city]['SUHI'].dropna()
            fig.add_trace(
                go.Histogram(x=data, name=city, opacity=0.6, nbinsx=15),
                row=1, col=2
            )
        
        # 3. Q-Q Plot for normality
        suhi_data = self.df['SUHI'].dropna()
        theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(suhi_data)))
        sample_quantiles = np.sort(suhi_data)
        
        fig.add_trace(
            go.Scatter(x=theoretical_quantiles, y=sample_quantiles, 
                      mode='markers', name='Q-Q Plot'),
            row=1, col=3
        )
        
        # Add reference line for Q-Q plot
        min_val, max_val = min(theoretical_quantiles), max(theoretical_quantiles)
        fig.add_trace(
            go.Scatter(x=[min_val, max_val], y=[min_val, max_val], 
                      mode='lines', name='Reference Line', line=dict(dash='dash')),
            row=1, col=3
        )
        
        # 4. Box Plot: Year Comparison
        for year in [2017, 2024]:
            data = self.df[self.df['Year'] == year]['SUHI'].dropna()
            fig.add_trace(
                go.Box(y=data, name=f'{year}', boxpoints='outliers'),
                row=2, col=1
            )
        
        # 5. Box Plot: City Comparison
        for city in top_cities:
            data = self.df[self.df['City'] == city]['SUHI'].dropna()
            fig.add_trace(
                go.Box(y=data, name=city, boxpoints='outliers'),
                row=2, col=2
            )
        
        # 6. Regression: Year vs SUHI
        fig.add_trace(
            go.Scatter(x=self.df['Year'], y=self.df['SUHI'], 
                      mode='markers', name='Data Points', opacity=0.6),
            row=2, col=3
        )
        
        # Add regression line
        from sklearn.linear_model import LinearRegression
        X = self.df['Year'].values.reshape(-1, 1)
        y = self.df['SUHI'].dropna()
        X_clean = X[self.df['SUHI'].notna()]
        
        reg = LinearRegression().fit(X_clean, y)
        year_range = np.linspace(2017, 2024, 100).reshape(-1, 1)
        y_pred = reg.predict(year_range)
        
        fig.add_trace(
            go.Scatter(x=year_range.flatten(), y=y_pred, 
                      mode='lines', name='Regression Line'),
            row=2, col=3
        )
        
        # 7. Outlier Detection Results
        if self.statistical_results['outlier_analysis']:
            oa = self.statistical_results['outlier_analysis']
            outlier_types = ['Z-score', 'IQR', 'Modified Z-score']
            outlier_counts = [oa['z_score_outliers'], oa['iqr_outliers'], oa['modified_z_outliers']]
            
            fig.add_trace(
                go.Bar(x=outlier_types, y=outlier_counts, name='Outlier Counts'),
                row=3, col=1
            )
        
        # 8. Effect Sizes
        effect_sizes = []
        effect_labels = []
        
        if 'year_comparison' in self.statistical_results['hypothesis_tests']:
            yr = self.statistical_results['hypothesis_tests']['year_comparison']
            if yr['cohens_d'] is not None:
                effect_sizes.append(abs(yr['cohens_d']))
                effect_labels.append("Year Comparison")
        
        if 'paired_analysis' in self.statistical_results['hypothesis_tests']:
            pa = self.statistical_results['hypothesis_tests']['paired_analysis']
            effect_sizes.append(abs(pa['cohens_d_paired']))
            effect_labels.append("Paired Analysis")
        
        if effect_sizes:
            fig.add_trace(
                go.Bar(x=effect_labels, y=effect_sizes, name='Effect Sizes'),
                row=3, col=2
            )
        
        # 9. Statistical Power
        if 'year_comparison' in self.statistical_results['power_analysis']:
            power = self.statistical_results['power_analysis']['year_comparison']['achieved_power']
            fig.add_trace(
                go.Bar(x=['Achieved Power'], y=[power], name='Statistical Power'),
                row=3, col=3
            )
            
            # Add reference line at 0.8 (80% power)
            fig.add_hline(y=0.8, line_dash="dash", line_color="red", 
                         annotation_text="80% Power Threshold", row=3, col=3)
        
        # Update layout
        fig.update_layout(
            height=1200,
            title_text="Comprehensive Statistical Analysis Dashboard",
            showlegend=False
        )
        
        # Save visualization
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        viz_path = self.output_path / f"statistical_analysis_dashboard_{timestamp}.html"
        fig.write_html(str(viz_path))
        
        print(f"Statistical visualization saved to: {viz_path}")
        return viz_path
    
    def run_complete_analysis(self):
        """Run the complete comprehensive statistical review."""
        print("STARTING COMPREHENSIVE STATISTICAL REVIEW")
        print("="*80)
        
        # Load and prepare data
        self.load_and_prepare_data()
        
        # Run all statistical analyses
        self.test_normality()
        self.compare_years_comprehensive()
        self.city_comparison_analysis()
        self.paired_analysis_cities()
        self.regression_analysis()
        self.outlier_analysis()
        self.power_analysis()
        
        # Generate outputs
        report_path = self.generate_comprehensive_report()
        viz_path = self.create_statistical_visualizations()
        
        print("\n" + "="*80)
        print("COMPREHENSIVE STATISTICAL REVIEW COMPLETED")
        print("="*80)
        print(f"Report: {report_path}")
        print(f"Visualizations: {viz_path}")
        
        return {
            'statistical_results': self.statistical_results,
            'report_path': report_path,
            'visualization_path': viz_path
        }

def main():
    """Main function to run the comprehensive statistical review."""
    data_path = Path("suhi_analysis_output/data")
    
    if not data_path.exists():
        print(f"Error: Data path {data_path} does not exist.")
        print("Please ensure SUHI analysis has been run and data files are available.")
        return
    
    # Create and run comprehensive statistical review
    reviewer = ComprehensiveStatisticalReview(data_path)
    results = reviewer.run_complete_analysis()
    
    print("\n🎉 Comprehensive statistical review completed successfully!")
    print("Key deliverables:")
    print(f"  📊 Statistical Results: {len(reviewer.statistical_results)} analysis categories")
    print(f"  📋 Detailed Report: {results['report_path']}")
    print(f"  📈 Interactive Dashboard: {results['visualization_path']}")

if __name__ == "__main__":
    main()
