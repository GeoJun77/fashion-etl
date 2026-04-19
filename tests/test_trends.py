# tests/test_trends.py
# Tests the trend analyzer on the database

from src.transformers.trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer()
report = analyzer.analyze()

print(report.summary())
