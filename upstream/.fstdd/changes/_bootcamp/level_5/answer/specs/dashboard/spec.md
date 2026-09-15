# Spec: Dashboard + Report

## ADDED Requirements

### Req: Dashboard SHALL display KPIs
#### Scenario: Load
- **GIVEN** user has data
- **WHEN** dashboard loads
- **THEN** system SHALL display KPI cards

### Req: Report SHALL export PDF
#### Scenario: Export
- **GIVEN** dashboard has data
- **WHEN** user clicks export
- **THEN** system SHALL generate PDF
