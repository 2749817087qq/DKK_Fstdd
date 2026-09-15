# Spec: API Rate Limit

## ADDED Requirements

### Req: Rate limit enforcement
System SHALL enforce 100 req/min per IP.

#### Scenario: Normal
- **GIVEN** IP has 99 requests
- **WHEN** IP makes 1 more
- **THEN** system SHALL return 200

#### Scenario: Exceeded
- **GIVEN** IP has 100 requests
- **WHEN** IP makes 1 more
- **THEN** system SHALL return 429
- **AND** SHALL include Retry-After
