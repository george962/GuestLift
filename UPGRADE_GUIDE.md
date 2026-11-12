# Upgrade v0.5 → v0.6

- Full replacement files: this folder contains a complete codebase based on v0.5; backend and tests remain.
- Existing project directory on Mac can remain `~/GuestLift`, and the GitHub repo stays `george962/GuestLift`.
- Copy the extracted **contents** of this release into your project; preserve `.git/`, your personal `.env` and database volume.
- Do not unzip anything if the files are already in your project folder.
- Starting command is `docker compose up --build -d`.
- New navigation, account pages, animated tour and marketing design do not require a data migration.
- Only the public-facing name changes to a working label. Internal `GUESTLIFT_*` environment variables remain so existing setups keep working.
- This release is not a production merchant-service launch; no real account or billing functionality works until you configure external providers.
