#!/usr/bin/env python3
"""
Debug winsorized scaling function
"""

import numpy as np
import pandas as pd

def test_winsorized_function():
    """Debug the winsorized percentile function"""
    
    print("Debugging Winsorized Percentile Function")
    print("=" * 50)
    
    # Test values with extreme outlier
    test_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
    extreme_value = 100
    
    print(f"Test values: {test_values}")
    print(f"Testing extreme value: {extreme_value}")
    print()
    
    # Manual calculation
    s = pd.Series(test_values)
    p2 = s.quantile(0.02)
    p98 = s.quantile(0.98)
    
    print(f"2nd percentile: {p2}")
    print(f"98th percentile: {p98}")
    
    # Winsorize
    clipped_value = np.clip(extreme_value, p2, p98)
    print(f"Clipped value: {clipped_value}")
    
    # Scale
    if p98 != p2:
        scaled = (clipped_value - p2) / (p98 - p2)
        print(f"Scaled value: {scaled}")
    else:
        print("Cannot scale - p2 == p98")
    
    print()
    print("Issue Analysis:")
    print("The winsorized function may still return 1.0 if the extreme value")
    print("happens to be at the 98th percentile or above.")
    print("With only 10 values, the 98th percentile is still the max value.")
    print()
    print("For a 14-city dataset:")
    cities = ['Tashkent', 'Nukus', 'Andijan', 'Bukhara', 'Samarkand', 'Namangan', 
              'Jizzakh', 'Qarshi', 'Navoiy', 'Termez', 'Gulistan', 'Nurafshon', 
              'Fergana', 'Urgench']
    
    print(f"Number of cities: {len(cities)}")
    print(f"2nd percentile position: {0.02 * len(cities):.1f}")
    print(f"98th percentile position: {0.98 * len(cities):.1f}")
    print()
    print("With 14 cities, the 98th percentile is still the top city!")
    print("Need to use more aggressive percentiles like 5th-95th or 10th-90th")

if __name__ == "__main__":
    test_winsorized_function()
