# Security policy

Report vulnerabilities privately through GitHub's **Report a vulnerability** button (Security tab → Advisories). Do not open public issues for security problems.

Never commit secrets. `.env` is gitignored, CI runs gitleaks on every push, and GitHub push protection blocks known secret formats.
