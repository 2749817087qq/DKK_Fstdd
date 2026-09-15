# Spec

### Req: Rate limit
System SHALL enforce 100 req/min.

#### Scenario: Normal
- **GIVEN** IP has 99 req
- **WHEN** 1 more
- **THEN** SHALL return 200
