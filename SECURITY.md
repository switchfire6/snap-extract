# Security

The current `main` branch receives security fixes. This project does not provide a security support SLA.

Report vulnerabilities privately through the repository's **Security → Report a vulnerability** page when available. Do not include credentials, account IDs, local collection files, or private paths in a public issue. If private reporting is unavailable, open an issue requesting a private reporting channel without disclosing the vulnerability.

Snap Extract reads a local collection file and retrieves a public card catalog over HTTPS. It does not need a Marvel Snap or GitHub token. Catalog redirects must remain on the same HTTPS origin, response size is bounded, and cache fields are validated before replacing the previous cache. The catalog is parsed as data, never executed.

CSV/TSV cells are quoted, and text beginning with formula markers or dangerous control characters is prefixed with an apostrophe; numeric card values remain numeric. Spreadsheet software varies and can reinterpret files after editing or re-saving. JSON preserves the original data without spreadsheet interpretation.

Exports cannot be saved inside the selected collection's folder or the default SNAP state folder. CLI exports without `--force` publish the complete file only if the destination is still absent; a concurrent writer's file is preserved. Filesystems without hard-link support fail safely for this operation; use a local NTFS destination, or `--force` only when replacing the destination is intended.

The installer runs per-user without requesting elevation. It adds launch shortcuts, with no service, scheduled task, or startup entry. Uninstall preserves user-created files, preferences, and catalog data. Downloads currently lack a code-signing certificate. Checksums detect corruption but do not authenticate the publisher.

CI audits declared Python dependencies and tests security-sensitive behavior. These checks do not establish the absence of all vulnerabilities; keep the bundled Python, Tcl/Tk, build tools, and Windows current.

Keep game state files, generated exports, fetched catalogs, settings, and credentials out of Git. If a credential is exposed, revoke it at the provider and issue a replacement; deleting the text does not invalidate the credential.
