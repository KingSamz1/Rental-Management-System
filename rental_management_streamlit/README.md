# Rental Management (Streamlit MVP)

A working rental management system for Ugandan landlords: properties, units,
tenants, monthly rent, payments (including Mobile Money references), water
bills, deposits, advance rent, PDF receipts, reports/CSV export, and
WhatsApp reminder preparation.

## Setup

```bash
cd rental_management_streamlit
python -m venv .venv
```

Activate the environment:

- Windows: `.venv\Scripts\activate`
- Linux/Mac: `source .venv/bin/activate`

Then:

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` and set your own username/password and
landlord details, then run:

```bash
streamlit run app.py
```

The SQLite database (`data/rental.db`) is created automatically on first
run — no manual setup needed.

## Suggested first walkthrough

1. **Properties & Units** — add a property, then add its units with rent
   and water rates.
2. **Tenants** — assign a tenant to a vacant unit.
3. **Rent** — generate this month's rent charge (either bulk for all active
   tenants, or one at a time).
4. **Payments** — record a payment against that tenant (try Mobile Money to
   see the transaction reference field), and download the auto-generated
   PDF receipt.
5. **Dashboard** — check that the tenant balance updated correctly.
6. **Reminders** — for anyone still owing, preview the WhatsApp message and
   open the click-to-chat link.
7. **Reports** — export balances/payments/charges as CSV.

## Project layout

```
app.py                  Dashboard (entry point)
pages/                  One file per sidebar page
utils/db.py             SQLite schema + connection
utils/logic.py          All business logic (properties, tenants, rent, balances)
utils/receipts.py       PDF receipt generation (reportlab)
utils/whatsapp.py       Reminder message builder + pluggable send interface
utils/auth.py           Simple login gate
data/rental.db          Created automatically — your data lives here
receipts/               Generated PDF receipts land here
```

## What this is (and isn't)

This is a working MVP foundation, tested end-to-end (property → unit →
tenant → rent charge → payment → balance → PDF receipt). Before using it
commercially with real landlords or tenants, you should still strengthen:

- **Authentication** — currently a single hardcoded username/password in
  `secrets.toml`, no hashing, no multi-user support, no session expiry.
- **Backups** — nothing backs up `data/rental.db` automatically.
- **Audit logs** — there's no record of who changed what.
- **Deployment security** — run behind HTTPS, keep `secrets.toml` out of
  version control (it's already gitignored-style excluded — don't commit it).
- **WhatsApp sending** — `utils/whatsapp.py` prepares messages and gives a
  manual click-to-chat link today. `send_via_provider()` is left
  unimplemented (raises `NotImplementedError`) so it's obvious where to plug
  in the WhatsApp Business Cloud API, Twilio, or another aggregator.
- **Mobile Money** — payments currently store a manually-entered transaction
  reference. Real API reconciliation (MTN/Airtel APIs) would remove the
  manual-entry step.

## Balance logic, in case you're auditing it

A tenant's balance = sum of all `rent_charges` (rent + water + other) for
them, minus sum of all payments with type `rent`/`water`/`other`. Deposits
and advance rent are tracked as separate ledgers and are **not**
automatically netted into the rent balance — they're credits held for a
specific purpose (deposit refund, or a future month's rent), and applying
them is a deliberate action you take on the Payments page when that time
comes, not an automatic offset.
