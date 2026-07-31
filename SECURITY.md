# Security policy

## Supported versions

Until 1.0, only the latest released version receives security fixes.

## Reporting

Please use GitHub's private security advisory flow for vulnerabilities. Do not
open a public issue containing secrets, private project content, or an
unpatched exploit.

## Data boundary

Cairn Lite reads and writes only inside the project path supplied to the CLI.
It has no telemetry, network client, credential store, or external
knowledge-base integration.

The default protocol prohibits external knowledge-base writes without explicit
human confirmation.
