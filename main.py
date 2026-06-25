from src.bronze import run_bronze_layer
from src.silver import run_silver_layer
from src.validate import run_data_quality_layer
from src.gold_dimensions import run_gold_dimensions_layer
from src.gold_facts import run_gold_facts_layer


def main():
    """
    Full pipeline execution:
    1. Bronze Layer  - Raw source copy
    2. Silver Layer  - Cleaned transformed data
    3. DQ Layer      - Data quality report
    4. Gold Dims     - 8 dimension tables
    5. Gold Facts    - 4 fact tables
    """

    run_bronze_layer()
    run_silver_layer()
    run_data_quality_layer()
    run_gold_dimensions_layer()
    run_gold_facts_layer()


if __name__ == "__main__":
    main()