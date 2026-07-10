# Security Policy

## Project Scope

NavigatorEdu is a portfolio and demonstration application built around bundled synthetic content packs. It is not intended for operational, clinical, diagnostic, or patient-care use.

The repository and hosted demo must not contain protected health information, real patient records, credentials, private keys, employer-confidential information, internal procedures, or proprietary clinical-system content.

## Supported Version

Security and safety fixes are applied to the current `main` branch and hosted demonstration. Historical branches and old commits are not maintained as separate supported releases.

## Reporting a Vulnerability

Do not publish sensitive exploit details, credentials, private information, or harmful payloads in a public issue.

Use GitHub's private vulnerability-reporting or Security Advisory feature when it is available for this repository. Otherwise, contact the repository owner through the GitHub profile and establish a private reporting channel before sharing sensitive details.

A useful report includes:

- Affected route, component, workflow, or dependency
- Reproduction steps using synthetic data only
- Expected and observed behavior
- Potential impact
- Browser, Python, and deployment context when relevant
- A proposed mitigation, when known

## Data-Safety Incidents

If real personal data, PHI, credentials, private keys, tokens, or employer-confidential material is accidentally committed or deployed:

1. Treat the material as compromised.
2. Revoke or rotate affected credentials immediately.
3. Remove the material from the active branch and deployment.
4. Assess whether Git history or deployment logs require remediation.
5. Document the response without reproducing the sensitive material.

Deleting a file in a later commit does not remove it from Git history.

## Hosted-Demo Boundary

The hosted instance intentionally has no user accounts, no uploads, and no durable user-data storage. Content-pack selection is limited to bundled, allowlisted synthetic packs. A vulnerability fix does not change the application's stated boundary: it remains a demonstration system, not a clinical or operational product.
