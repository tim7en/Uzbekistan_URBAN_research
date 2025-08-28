# Overcrowding Climate Risk Assessment Fix

## Problem Statement
There was a flaw in the climate risk assessment where schools with overcapacity were not properly accounting for multiple shifts, which reduce overcrowding risk.

## Root Cause Analysis
1. **Field Name Mismatch**: The climate risk assessment was looking for `school_utilization_rate` but the social sector module provides `utilization_rate`
2. **Multiple Shifts Calculation**: Actually working correctly in `social_sector.py` - effective capacity = capacity × shifts
3. **Vulnerability Logic**: The previous logic didn't properly handle utilization rates above 100% after accounting for shifts

## Solution Implemented

### Fixed Field Name Mismatch
**File**: `services/climate_risk_assessment.py`
**Change**: Updated `_calculate_utilization_rate_vulnerability()` to use `utilization_rate` instead of `school_utilization_rate`

### Improved Vulnerability Calculation Logic
**New Logic**:
- Utilization < 50%: Under-utilization vulnerability (inefficient infrastructure)
- Utilization 50-100%: Minimal vulnerability (optimal range)
- Utilization > 100%: True overcrowding vulnerability (despite multiple shifts)

**Formula**:
```python
if utilization_rate < 0.5:
    vulnerability = (0.5 - utilization_rate) * 1.5  # Under-utilization
elif utilization_rate <= 1.0:
    vulnerability = 0.1  # Optimal range
else:
    excess = utilization_rate - 1.0
    vulnerability = 0.3 + min(0.7, excess * 1.0)  # Overcrowding
```

## Verification Results

| City | Utilization Rate | Multiple Shifts | Vulnerability | Status |
|------|------------------|-----------------|---------------|--------|
| Samarkand | 145.1% | 90.7% of schools | 0.751 | High overcrowding |
| Nurafshon | 110.1% | 69.7% of schools | 0.401 | Moderate overcrowding |
| Qarshi | 130.5% | 91.4% of schools | 0.605 | High overcrowding |

## Key Improvements
1. ✅ **Multiple Shifts Properly Considered**: Effective capacity already calculated as capacity × shifts
2. ✅ **Field Name Mismatch Resolved**: Now correctly reads `utilization_rate` from social sector data
3. ✅ **True Overcrowding Detection**: Utilization >100% after shifts indicates genuine overcrowding
4. ✅ **Accurate Risk Assessment**: Climate vulnerability now reflects real overcrowding risk

## Impact
- Schools with multiple shifts are now correctly assessed for overcrowding risk
- Climate risk assessment accurately reflects whether shifts are sufficient to address capacity issues
- High utilization rates (>100%) after accounting for shifts properly trigger high vulnerability scores
- The assessment now distinguishes between efficient use of capacity and true overcrowding

This fix ensures that the climate risk assessment correctly accounts for multiple shifts in schools while still identifying true overcrowding situations where even multiple shifts cannot address capacity constraints.