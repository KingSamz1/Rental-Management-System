# Rental Management System (RMS)

A Python and Streamlit application for landlords and guesthouse operators to organise property operations in one place.

RMS brings together property and unit records, tenant information, rent and water charges, payment records, deposits, advance rent, PDF receipts, reports and WhatsApp reminder preparation.

## Project overview

- **Project:** Rental Management System (RMS), presented in the application as LandlordPro
- **Developer:** Samuel — [@KingSamz1](https://github.com/KingSamz1)
- **Languages and tools:** Python, Streamlit, Turso/libSQL HTTP API, Pandas and ReportLab
- **Status:** Independently developed application / evolving MVP

## Features in the application

- Property and unit management
- Tenant records, occupancy status and document attachment
- Monthly rent and water charge tracking
- Payment records, including manually entered Mobile Money references
- Deposit and advance-rent records
- PDF receipt generation
- Income, payment and balance reports with CSV export
- WhatsApp reminder preparation and click-to-chat links
- Account registration, login, password reset and subscription-related screens
- Currency selection and business profile settings

## Technology and architecture

- **Python** — application and business logic
- **Streamlit** — interactive web interface
- **Turso/libSQL** — cloud database accessed through its HTTP API
- **Pandas** — report tables and data exports
- **ReportLab** — PDF receipt generation
- **Requests** — HTTP communication with the database service

## Repository structure

```text
app.py                  Streamlit application entry point
pages/                  Properties, tenants, rent, payments, reports, etc.
utils/db.py             Turso database access, schema and account helpers
utils/logic.py          Rental, tenant, charge and payment business logic
utils/auth.py           Login, registration and password-reset interface
utils/receipts.py       PDF receipt generation
utils/whatsapp.py       Reminder preparation and click-to-chat links
utils/subscription.py   Trial, renewal-code and subscription logic
utils/theme.py          Shared interface styling and components
utils/i18n.py           Language and translation support
requirements.txt        Python dependencies
```

## Run locally

1. Install Python 3.10 or newer.
2. Clone the repository and open its folder.
3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows PowerShell
   .venv\\Scripts\\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create `.streamlit/secrets.toml` locally. Add your own Turso credentials and initial account details:

   ```toml
   [turso]
   url = "libsql://YOUR-DATABASE.turso.io"
   token = "YOUR_TURSO_AUTH_TOKEN"

   [auth]
   username = "YOUR_INITIAL_USERNAME"
   password = "YOUR_INITIAL_PASSWORD"

   [landlord]
   business_name = "Your Business Name"
   currency = "UGX"
   phone = ""

   # Optional: used only to create the reserved admin account
   # when it does not already exist in a fresh database.
   [admin]
   password = "A-UNIQUE-STRONG-ADMIN-PASSWORD"
   ```

   The `[auth]` section is used only when the database has no accounts yet. Existing accounts keep their own passwords. The optional `[admin]` setting provisions the administrator account on a fresh database; it does not reset an existing administrator password.

6. Start the application:

   ```bash
   streamlit run app.py
   ```

Never commit real secrets, tenant records, identity documents, database files or generated receipts.

## Current implementation notes

- Mobile Money payments store a transaction reference entered by the user; automatic provider reconciliation is not included.
- WhatsApp reminders can be prepared and opened as click-to-chat links. Automated sending through the WhatsApp Business API or another provider is not implemented in the current reminder module.
- Subscription and renewal-code screens are included; a production payment-gateway integration should be assessed separately.
- The current password helper uses salted SHA-256. A password-specific password-hashing algorithm should be adopted before production use.
- Account ownership checks, backups, audit logging, upload validation and production deployment security need further review before handling real customers' sensitive records.

This repository is shared as a software-development portfolio and demonstration. Do not use it with real tenant identity documents or financial records without completing a security review and configuring appropriate access controls, backups and deployment protections.

## Developer

Built by **Samuel** as an independent software project to explore practical application development, database-backed workflows, user interfaces and business process automation.

GitHub: [@KingSamz1](https://github.com/KingSamz1)
