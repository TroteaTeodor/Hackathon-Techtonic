# Spec Delta

## Purpose

Ensures that only authenticated users reach Foresight data, that customers can only ever see their own data, and that advisor functions are limited to advisors.

## ADDED Requirements

### Requirement: Login and session
Users SHALL log in with a username and password. On success, the system SHALL set an HTTP-only, SameSite=Lax session cookie that expires after 8 hours, and return the user's role and display name. Logging out SHALL clear the cookie.

#### Scenario: Successful login
- **WHEN** a demo user logs in with the correct password
- **THEN** the response sets an HTTP-only session cookie and returns their role

#### Scenario: Wrong password
- **WHEN** a login uses the wrong password or an unknown username
- **THEN** the response is 401 with the same generic message in both cases

### Requirement: Login rate limiting
The system SHALL reject more than 5 failed login attempts per username and client address within 5 minutes with a 429 status.

#### Scenario: Brute force attempt
- **WHEN** a 6th failed login for the same username arrives within 5 minutes
- **THEN** the response is 429, even if the password is correct

### Requirement: Authentication required
Every endpoint except login, logout and health SHALL require a valid session. Without one it SHALL return 401.

#### Scenario: No cookie
- **WHEN** a request to a customer or advisor endpoint has no valid session cookie
- **THEN** the response is 401

### Requirement: Role-based authorization
Advisor endpoints SHALL require the `advisor` role and SHALL return 403 for customers. Customer endpoints SHALL require the `customer` role.

#### Scenario: Customer tries the advisor console
- **WHEN** a logged-in customer calls the customer list endpoint
- **THEN** the response is 403

### Requirement: Customer data isolation
Customer endpoints SHALL identify the customer from the session only, never from a request parameter. Any customer action on an intervention SHALL require that the intervention belongs to that customer, and SHALL respond 404 otherwise.

#### Scenario: IDOR attempt
- **WHEN** customer Sara sends feedback on an intervention ID that belongs to another customer
- **THEN** the response is 404 and the intervention is unchanged

### Requirement: Secrets and passwords
Passwords SHALL be stored only as salted hashes. The session signing secret, demo password and AI key SHALL come from environment variables and SHALL NOT be committed. The backend SHALL refuse to start if the session secret is missing or shorter than 32 characters.

#### Scenario: Missing secret
- **WHEN** the backend starts without `SESSION_SECRET`
- **THEN** startup fails with a clear error message

### Requirement: Cross-origin policy
The API SHALL only accept credentialed cross-origin requests from the configured frontend origins.

#### Scenario: Unknown origin
- **WHEN** a browser request comes from an origin not in the allowed list
- **THEN** the response carries no CORS allow headers for that origin
