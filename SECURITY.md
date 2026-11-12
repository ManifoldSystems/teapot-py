# Security

Security fixes target the current `main` branch; there is no separate long-term
support line. This client is experimental.

Use **Security → Report a vulnerability** on GitHub when available. Otherwise,
open an issue titled **Private security contact requested**, without technical
details or credentials, so a maintainer can arrange a private channel.

Privately include the affected commit/version, reproduction steps, and impact.
Use test endpoints and redact request credentials, addresses, and personal data.

The proxy username selects an exit node; it is not an authentication credential.
The library expects a trusted local Teapot agent. HTTPS protects traffic to the
destination; plain HTTP does not hide request contents from an exit node.
Live tests send real traffic and should only use your own mesh.

See the [agent security policy](https://github.com/ManifoldSystems/teapot/blob/main/SECURITY.md)
for deployment boundaries.
