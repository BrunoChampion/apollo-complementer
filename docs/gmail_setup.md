# Gmail Drafts Setup

Phase 8 creates Gmail drafts only. It never sends email.

## OAuth Scope

Use the minimal compose scope:

```text
https://www.googleapis.com/auth/gmail.compose
```

## Backend Environment

Set:

```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

The refresh token must belong to the Gmail account where drafts should be created.

## Get A Refresh Token

1. In Google Cloud Console, create an OAuth client.
2. Use an OAuth client type that supports a localhost redirect, such as `Desktop app`.
3. Put the client values in the root `.env`:

```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

4. Run:

```bash
python scripts/get_gmail_refresh_token.py
```

5. Approve the Gmail consent screen. The script prints:

```bash
GOOGLE_REFRESH_TOKEN=...
```

6. Paste that value into the root `.env`.

If Google does not return a refresh token, revoke the app's access in your Google Account permissions and run the script again. The script requests `access_type=offline` and `prompt=consent`.

## Sheet Requirements

For `action = create_gmail_draft`, a row must have:

```text
approved = TRUE
prospect_email
final_message or revised_draft or email_draft
```

Subject priority:

```text
final_subject -> email_subject -> "Idea para {company_name}"
```

Idempotency:

```text
If gmail_draft_id already exists, the row is not selected for draft creation.
```

## Manual Validation

1. Approve a drafted/revised row in Google Sheets.
2. Set `action = create_gmail_draft`.
3. Run `Revenue Copilot -> Crear borradores Gmail aprobados`.
4. Confirm the Sheet gets `gmail_draft_id`, `gmail_draft_url`, and `status = gmail_draft_created`.
5. Open Gmail and review/send manually.
