# tests/test_quality.py
# Tests the quality checks on the database

from src.quality.checks import QualityChecker

checker = QualityChecker()
report = checker.run(run_id=1)

print(report.summary())