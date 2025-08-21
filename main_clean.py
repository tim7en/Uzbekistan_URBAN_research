"""Orchestrator entrypoint for SUHI analysis (minimal).

Delegates all heavy work to the refactored `services` package. This file
is intentionally tiny so it's easy to run a quick smoke test or use as the
CI entrypoint.
"""

from services import gee, utils, pipeline


def main() -> None:
    print("COMPREHENSIVE SUHI ANALYSIS ORCHESTRATOR (minimal)")

    if not gee.initialize_gee():
        print("GEE initialization failed. Exiting.")
        return

    gee.test_dataset_availability()
    utils.create_output_directories()

    cities = list(utils.UZBEKISTAN_CITIES.keys())
    if not cities:
        print("No cities configured in services.utils.UZBEKISTAN_CITIES")
        return

    city = cities[0]
    year = 2017

    results = pipeline.run_comprehensive_analysis(city, year)

    print(f"Analysis complete for {city} ({year})")
    print("Result keys:", list(results.keys()))


if __name__ == '__main__':
    main()
