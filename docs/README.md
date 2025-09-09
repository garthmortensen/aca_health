# Star Data Warehouse Documentation

This repository automatically generates and publishes dbt documentation to GitHub Pages.

## [View Live Documentation](https://garthmortensen.github.io/star/)

### Data Quality Tests
- **25 dbt-expectations tests** covering all staging sources
- Regex validation for IDs (CLM[0-9]{7}, MBR[0-9]{6})
- Date range validations
- Value range and set validations
- **100% test pass rate**

### Data Dictionary
- Complete column descriptions for all tables
- Data types and constraints
- Source system mappings
- Business logic documentation

### Data Architecture
- **Staging Layer**: Raw data validation and cleaning
- **Analytics Layer**: Dimensional models (dims/facts)
- **Semantic Layer**: Business metrics and aggregations

### Data Lineage
- Visual dependency graphs
- Source-to-target mappings
- Impact analysis capabilities

## Local Development

To generate docs locally:
```bash
cd transform
dbt docs generate
dbt docs serve
```

## Auto-Updates

Documentation is automatically updated on every push to the `main` branch via GitHub Actions.
