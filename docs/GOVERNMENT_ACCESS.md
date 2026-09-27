# Government access and protected evidence

Government operations, fleet telemetry, camera previews, detection ingestion, video uploads, job status, annotated videos, detected images and detection JSON require a valid government bearer token at the backend. Citizen tokens do not grant this access, even if their subject matches the government username. Tokens with invalid signatures, expired timestamps or no expiry are rejected.

The public portal continues to receive map alerts, coordinates and route-planning information. Its event metadata is limited to explicit map-presentation fields. OCR results, registration numbers, arbitrary media fields and device IDs are not included in public map responses.

## Portal sessions

Both government entry points verify `/api/v1/government/auth-check` before rendering protected content. Adding arbitrary text to browser storage does not pass this check. Sessions are rechecked on focus and every minute; the supplied expiry also schedules sign-out. Authorization failures remove the session and unmount protected content. Media blob URLs are revoked when their viewers unmount. Government tokens use session storage, including the legacy government entry in the citizen application; persistent legacy tokens are not reused.

Opening a government URL without credentials shows the sign-in entry. The frontend HTML/JavaScript and public icons are not private data; the backend remains the authority for all protected operations and media bytes.

## File access

Both Vite development servers now allow file serving only from their own frontend directory and the shared UI directory. The previous project-wide file allowance exposed evidence through `/@fs/` URLs even though the evidence API required authentication. Backend files, output videos, detected frames, datasets and runtime files cannot be served through that route now. Do not widen the allow-list to the entire project.

Keep evidence outside portal `public` and `dist` directories. Government media is fetched with the authorization header, then displayed using a revocable blob URL; a bare media URL without that header is rejected. Protected responses use `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff`.

## Sign-in and deployment scope

The existing configured government username/password remain in the ignored backend environment file. Comparisons use constant-time comparison. Five failed attempts from the same client address within five minutes result in HTTP 429 with `Retry-After`; a successful sign-in clears its attempt counter. Counters are bounded and process-local, matching `start.ps1`'s single API process. A multi-worker deployment needs a shared limiter or gateway rate limit.

This change hardens the current local application; it does not deploy a public service. For deployment, serve the production frontend builds over HTTPS, keep backend/media storage outside static roots and keep credentials on the server/authorized edge device. Files already downloaded by an authenticated operator are outside browser-session control. Signing out removes the local bearer token; a separately copied valid bearer token remains usable until its expiry because server-side token revocation is not implemented.

## Verification

`backend/tests/test_government_access.py` exercises every private route against anonymous, citizen, wrong-role, expired, forged and missing-expiry credentials. It also verifies valid government media/range access, protected video-upload workflows, public metadata filtering and login throttling.

`node scripts/check_fleet_render.mjs` checks that both government entry points render a session check before protected content. `node scripts/check_portal_imports.mjs` verifies live frontend imports still resolve after restricting file access. These are API and React-render checks, not browser click-through tests.

Implementation references: [Vite file-serving restrictions](https://vite.dev/config/server-options.html#server-fs-allow) and [FastAPI router dependencies](https://fastapi.tiangolo.com/tutorial/bigger-applications/#dependencies).
