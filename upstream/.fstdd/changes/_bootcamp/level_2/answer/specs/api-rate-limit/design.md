# API Rate Limit Design

## Decisions
### 1. Token bucket
**Why**: Simple, efficient.

## Architecture
Middleware -> TokenBucket -> 429
