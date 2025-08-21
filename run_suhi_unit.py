"""Runner for SUHI unit maps (2017-2024 by default).

Usage: python run_suhi_unit.py
"""
from services.gee import initialize_gee
from services.suhi_unit import run_batch

def main():
    ok = initialize_gee()
    if not ok:
        print('GEE initialization failed. Authenticate and try again.')
        return
    # Sample small batch to limit runtime and outputs
    cities = ['Tashkent','Nukus','Andijan']
    years = list(range(2017, 2025))
    results = run_batch(cities=cities, years=years, download_scale=100)
    print('SUHI batch complete. Summary:')
    for c in results:
        for y in results[c]:
            print(c, y, results[c][y].get('summary_json'))

if __name__ == '__main__':
    main()
