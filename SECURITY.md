# Security

The current `main` branch receives security fixes. This project does not provide a security support SLA.

Report vulnerabilities privately through the repository's **Security → Report a vulnerability** page when available. Do not include credentials, account IDs, local collection files, or private paths in a public issue. If private reporting is unavailable, open an issue requesting a private reporting channel without disclosing the vulnerability.

Snap Extract reads a local collection file and retrieves a public card catalog over HTTPS. It does not need a Marvel Snap or GitHub token. The catalog is parsed as data, never executed. Exported CSV/TSV text that could be interpreted as a spreadsheet formula is escaped; numeric card values remain numeric.

Keep game state files, generated exports, fetched catalogs, settings, and credentials out of Git. If a credential is exposed, revoke it at the provider and issue a replacement; deleting the text does not invalidate the credential.
