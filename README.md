# AFRICA ATONA

**Find your way, together.** Navigation platform for `https://africaatona.africandroid.world`, deployed on the existing Olamidepanel Debian server. This repository contains an initial beta, not a complete Waze replacement.

## Included

- Responsive road map with OpenStreetMap attribution, destination map picking, search, recenter, zoom and light/dark interface.
- Same-origin geocoding and OSRM-compatible routing adapters; alternative routes, route steps, one intermediate stop and different planning origin.
- GPS position and measured speed, foreground guidance, route overview, arrival detection and basic off-route recalculation. Route estimates are not verified live-traffic ETAs. GPS accuracy, road coverage and provider availability affect guidance.
- Road reports (11 categories), private account saved places including Home/Work, planned arrival dates and account deletion. SQLite persistence; password hashing, secure cookies, origin checks and rate limits.
- 551 language, variety and group preferences from the supplied inventory, separate interface/spoken-language/device-voice selections. Seven draft core-label dictionaries (English, French, Portuguese, Arabic, Swahili, Yoruba, Hausa); detailed screens and route text remain English. Other entries explicitly fall back to English. Registry IDs beginning `preference-` are internal choices, not ISO locale tags. Group names are not individual language support. Sign-language preferences have no avatar content.
- Android WebView foreground client with branded icon, HTTPS origin restriction, user location permission and external-browser links.
- GitHub Actions development APK build, versioned prerelease and checksum; deployment installs a selected APK only after checksum verification. Download UI becomes active only when the APK exists on the server.
- Ansible DNS, systemd, nginx, Let's Encrypt, daily SQLite backups/expiry cleanup and existing Olamidepanel Hosting Domains inventory integration.

## Still required for the full requested scope

Verified live traffic and congestion colors, traffic-aware rerouting, lane guidance, speed-limit/enforcement/camera data, specialized vehicle and road restriction routing, toll prices, fuel/EV/parking inventories and reservations, live audio integrations, calendar/contact sync, background navigation/departure notifications, voice reporting, custom recorded actors, full reviewed translations and dialect voices, sign-language navigation, community points/map editing, email password reset and verification, data export, Android Auto/CarPlay/Automotive and an iOS app are not implemented. No placeholder data is represented as live data. No police/camera or safety alert is generated without a data source.

## Local checks

Python 3.11+, Node for JavaScript syntax validation. No Python packages needed.

```bash
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 server.py
```

Local UI is `http://127.0.0.1:8097`. For browser account testing use an HTTPS reverse proxy and PUBLIC_URL; cookies are always Secure. Do not weaken cookies for deployment.

## Routing and search

Set `ATONA_ROUTING_URL` to an authorized OSRM-compatible HTTPS server base URL and `ATONA_GEOCODER_URL` to an authorized Nominatim-compatible HTTPS server base URL. Deployment deliberately requires these; public demo APIs are not assumed to be production services. No provider keys belong in browser files or Git. The current adapters do not implement authenticated vendor-specific APIs.

References: https://project-osrm.org/docs/v26.5.0/http and https://leafletjs.com/reference.html. Leaflet and OSM tiles currently load from external services; production deployment must meet their usage policies and traffic capacity. No offline maps or offline routing are included.

## Deploy on the existing server

Run on `181.214.149.146` in a root shell or via sudo. Requires the existing `olamidepanel` group and inventory. Choose provider URLs before running. Namecheap API access must be enabled and the server public IPv4 allowlisted. Inject credentials into the current environment without saving them to shell history or repository files:

- `NAMECHEAP_API_USER`, `NAMECHEAP_API_KEY`, `NAMECHEAP_USERNAME`, `NAMECHEAP_CLIENT_IP`.
- `ATONA_ROUTING_URL`, `ATONA_GEOCODER_URL`.
- Optional `ATONA_APK_TAG=atona-beta-<successful-run-number>`.

```bash
apt-get update
apt-get install -y git ansible
# First installation; choose another empty path if it already exists.
git clone https://github.com/olamidebello/Africaatona.git /opt/africaatona-source
cd /opt/africaatona-source
ansible-playbook -i localhost, -c local deploy/provision.yml
```

The requested hostname is a subdomain of your existing domain; it does not require a separate domain purchase. The DNS adapter merges `A africaatona -> 181.214.149.146`, reads the whole zone before writing, checks for concurrent edits and conflicting CNAME/AAAA entries, and refuses records it cannot preserve safely. Namecheap replaces the host list on setHosts, so preservation is mandatory. If the zone has mail metadata unavailable to the API or CAA/dynamic-DNS records, create this one A record in Namecheap manually and rerun with `-e provision_namecheap=false`.

TLS, health checks and inventory registration run only after DNS resolves to the server. The playbook adds the verified domain to `/var/lib/olamidepanel/hosted-domains.json` using the existing inventory layout and lock. It does not alter the hosting panel's source code or accounts. No remote operation has been verified merely by committing this playbook.

## Android app and downloads

Verified CI build: https://github.com/olamidebello/africanappsstore/releases/tag/atona-beta-2 (successful run 39337582062). The deployment playbook defaults to this pinned development release and installs its checksum-verified APK. APK SHA-256: `b3b8364596042ca86414afb17add09f9cff27282d991274a6f00dc583d1d7671`. Android compilation succeeded; no physical-device or road test has been performed. Server access is blocked in the authoring environment; DNS, TLS, runtime provider calls and website download deployment remain unverified.

The workflow builds `android/` using Java 17, Gradle 8.9, Android SDK 35 and AGP 8.7.3. Pushes changing Android source start the build. See Actions and the versioned `atona-beta-N` prerelease. These are development-signed APKs; configure a protected, stable production signing key and release process before distributing production upgrades or submitting to Google Play. Debug signing keys may differ between CI runs, requiring uninstall before upgrading.

The source is also published under `mobile/africa-atona/` in `olamidebello/africanappsstore` with its own build workflow. No existing app-store code is replaced. To deploy a successful app-store prerelease, set `ATONA_APK_TAG` and run:

```bash
ansible-playbook -i localhost, -c local deploy/provision.yml -e apk_repository=africanappsstore
```

Once installed, the website's Get Android app control serves `/downloads/africa-atona.apk`. Without an installed artifact it truthfully displays build pending. The APK loads the hosted service; it cannot work before hosting is live. Android background navigation is not supported and navigation stops when the app pauses.

## Operations and privacy

Runtime: `africaatona.service` on `127.0.0.1:8097`; data `/var/lib/africaatona`; protected environment `/etc/africaatona.env`. Daily `africaatona-maintenance.timer` removes expired reports/sessions and retains seven daily SQLite backups. Active reports expire from display after two hours. User data in backups can remain for seven days after account deletion. The in-app Help screen explains this privacy model. No continuous location trail is stored; submitted coordinates and provider queries leave the device. This beta needs operational monitoring, provider load testing and road testing before production navigation use.


## Automatic private providers and super administration

Run on the hosting server:

```bash
cd /opt/africaatona-source
git pull --ff-only origin main
ansible-playbook -i localhost, -c local deploy/auto-provision.yml
```

When neither external URL environment variable is set and the capacity check passes, this imports **Nigeria** OpenStreetMap data into private OSRM and Nominatim containers, validates route/search responses, and automatically configures `ROUTING_URL=http://127.0.0.1:5007` and `GEOCODER_URL=http://127.0.0.1:8087`. Only those exact loopback HTTP endpoints are accepted alongside the existing HTTPS provider option. The website remains public HTTPS; provider ports bind only to loopback. No API key or public demo endpoint is assumed. If using external providers instead, set both `ATONA_ROUTING_URL` and `ATONA_GEOCODER_URL` before running.

This regional deployment profile requires at least **16 GB RAM and 80 GiB free disk**. If either check fails, the automatic playbook skips map imports and deploys the website, HTTPS, super administration and APK with empty provider settings. The existing UI and API explicitly report routing and destination search as awaiting providers. No map engine or successful route is claimed in this mode. The playbook prints measured RAM and disk capacity. After upgrading capacity, rerun the same playbook to import providers, or supply both authorized external URLs. The initial geocoder import can take hours. Both imports have persistent state, named PostgreSQL storage, protected database credentials, container ownership labels, and first-use resolved image digests to prevent silent upgrades. Docker is installed only if absent. Dataset changes are refused rather than replacing existing databases. This does not provide all-Africa map coverage, live traffic, automatic map refresh, or off-host geocoder backups; those need a capacity and data-maintenance deployment plan. The dataset URL is recorded in `/var/lib/africaatona-providers/dataset.json`.

The automatic playbook then runs existing hosting/TLS/APK deployment with DNS changes disabled because the hostname is already configured. It still checks DNS before certificate provisioning. Existing Namecheap-enabled `deploy/provision.yml` remains available separately.

Super administration is available at `/admin.html` after deployment. The backend adds role/disabled columns and an audit table without replacing accounts. It supports account enable/disable, grant/remove super-admin access, session revocation, report deletion, database resource counts and audit history. Requests require a super-admin session; mutations additionally require the configured same-origin Origin header. No password hashes are exposed. It refuses self-disable and self-demotion.

The deployment explicitly promotes `ATONA_ADMIN_EMAIL` (default `dobcalldemo@gmail.com`) if that account exists, preserving its password. Otherwise it creates a random password and saves new credentials to root-only `/var/lib/africaatona-admin/credentials.json`; no password is printed by Ansible. Use your existing password for an existing account. The navigation includes an Administration link. Other domains' administrator accounts are independent.
