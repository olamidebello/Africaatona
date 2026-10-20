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

## Pull and deploy an existing installation

After the landing-page changes and playbook are published to GitHub, run on the hosting server:

```bash
cd /opt/africaatona-source
git pull --ff-only origin main
ansible-playbook -i localhost, -c local deploy/pull-and-deploy.yml
```

Or run from an Ansible controller with SSH access:

```bash
ansible-playbook -i 181.214.149.146, -u root deploy/pull-and-deploy.yml
```

The playbook pulls `main` into `/opt/africaatona-source` on the target server, refuses to discard local source edits, runs the application tests, and requires all landing-page assets before changing the installation. It snapshots the installed files, copies the server and web files, restarts `africaatona`, checks backend health, validates nginx and checks the public HTTPS homepage, stylesheet, script and map. A failed deployment restores the previous files and restarts the service. Snapshot paths are printed and retained for operator cleanup. The application database and protected environment remain in their existing locations; downloaded APKs, DNS and TLS are retained. This update playbook does not provision a new server or configure providers.

To deploy a specific published commit, append `-e atona_revision=<commit-sha>`. The homepage is `/`; the navigation application is `/map.html`.

## Navigation workflows and resource coverage

The map Menu now links saved places, planned drives, opt-in recent journeys, account/profile, map/privacy settings, support tickets, route overview/steps, stop navigation and feature availability. Destination cards support destination-link sharing and stop removal. Fuel, parking, charging and food buttons use the configured geocoder for place searches; they do not provide prices, availability or bookings.

Database migrations create `preferences`, `history`, `report_votes` and `support_tickets` without replacing existing tables. Settings sync and history are explicit account actions. History is off by default and limited to 100 destinations per account. Password changes verify the current password and revoke all sessions. Report confirmations allow one replaceable vote per account and reject self-confirmation. Support tickets are visible to their owner and super administrators, who can resolve them through the admin GUI. Existing origin checks, session authorization and rate limits apply to these endpoints. Account deletion removes the additional account records.

`web/features.json` is the item-by-item implementation/resource inventory displayed by Menu → Features & availability. It distinguishes implemented workflows from conditional provider features and work still requiring additional resources. Waze feature parity is **not complete**: live traffic/predictive ETA, live journey sharing, road-data alerts, specialized vehicle routing, avoidance profiles, parking/EV/fuel services, offline/background navigation, native car integrations, mail reset delivery and full translations require the listed implementation and resources. No Waze API, proprietary feed, account or map data is assumed. Reference: https://support.google.com/waze/?hl=en and https://www.waze.com/faq .

Deploy with the same single command:

```bash
cd /opt/africaatona-source && git pull --ff-only origin main && ansible-playbook -i localhost, -c local deploy/pull-and-deploy.yml
```

## Address search when no geocoder is configured

`pull-and-deploy.yml` now preserves an existing geocoder and otherwise selects Photon (`https://photon.komoot.io`, `GEOCODER_FORMAT=photon`). It snapshots the protected service environment along with application files, restarts the service, and verifies a real Lagos query through the backend. Failed checks restore both application files and configuration. Photon GeoJSON is converted into the existing destination-search response format.

The public Photon service permits reasonable project traffic but can throttle or withdraw access and offers no availability guarantee: https://github.com/komoot/photon#demo-server . This is a low-volume option, not a reserved production capacity allocation. Search is manual, proxied through one application instance, limited to one uncached request per 1.1 seconds across all users, and cached in SQLite for 24 hours with at most 1,000 entries. Concurrent or too-frequent uncached searches receive a retry response rather than queueing extra provider calls. Search addresses are shared with the configured provider; exact address coverage depends on its map data. No query relaxation silently replaces a house address with a city result.

For larger usage, configure your own Photon/Nominatim service or authorized commercial compatible endpoint in `/etc/africaatona.env`, then restart `africaatona`. Use `GEOCODER_FORMAT=photon` for Photon or `GEOCODER_FORMAT=nominatim` for a compatible Nominatim endpoint. The automatic configuration never selects the public Nominatim endpoint. Road routing is configured independently by `ROUTING_URL`; enabling address search alone does not enable turn-by-turn routes.


## African Pidgin language

Settings → Interface language includes **African Pidgin — Nigerian Pidgin (Naija)** (`pcm`) with draft core navigation labels and a translated destination-search placeholder. Existing Nigerian Pidgin selections using the legacy `preference-75` identifier migrate to `pcm` in the interface. The account settings API accepts and restores this choice. Cameroon and Ghanaian Pidgin remain separately listed preferences with English fallback; the Nigerian translation is not presented as a translation of those varieties. Detailed dialogs and route instructions still use English. Spoken output depends on installed device voices; selecting Pidgin does not install or guarantee a Pidgin voice.


## Map-first mobile home and route preview

The mobile map now stays behind a draggable bottom sheet. The handle is also a keyboard-operable expand/collapse button. Home includes microphone search, Home/Work/New shortcuts, recent destinations, an opt-in history-based destination suggestion with No/Drive there/info actions, and saved-address navigation for friends and family. No contact imports or inferred travel schedules are used. The microphone starts only after a confirmation; unsupported browsers use typed search.

Route preview shows a back action, origin/destination heading, clickable alternative route lines and map duration labels, road names, distance, estimated arrival, car/motorcycle selector, Avoid options, Leave later (saved planned drive), Go now and route steps. Estimates use the routing provider, without live or typical-traffic claims. Suggestions do not invent a trip time before requesting a route.

The existing car endpoint remains `ROUTING_URL`. To enable motorcycle selection, configure `MOTORCYCLE_ROUTING_URL` with a separate OSRM-compatible service prepared using an appropriate motorcycle road profile. Changing the request profile label alone does not create motorcycle routing. Declare only classes actually supported by your OSRM data via `ROUTING_EXCLUDES=toll,motorway,ferry,unpaved`, and separately `MOTORCYCLE_ROUTING_EXCLUDES` for that provider. OSRM profiles must support the declared classes and exclusion combinations. The backend passes validated selections as OSRM `exclude`; unsupported choices are disabled in the UI and rejected by the API. It never silently substitutes car routing for a motorcycle request. Reference: https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md .

These optional environment settings are preserved by the update playbook. Restart `africaatona` after changing provider configuration. The current default provisioning does not install a motorcycle-specific road graph or add traffic data.
