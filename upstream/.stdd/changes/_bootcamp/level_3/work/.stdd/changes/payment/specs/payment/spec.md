# Spec: Payment Module

## ADDED Requirements

### Req: Alipay SHALL be supported
#### Scenario: QR payment
- **GIVEN** user selects Alipay QR
- **WHEN** amount is 100 CNY
- **THEN** system SHALL generate valid QR code
- **AND** SHALL return payment_id
