# HubSpot Adapter Setup

Phase 12 is optional. The core Sheets -> draft -> Gmail flow does not depend on HubSpot.

## Create A Private App

1. Open HubSpot.
2. Go to Settings -> Integrations -> Private Apps.
3. Create a private app.
4. Grant the minimum scopes needed:

```text
crm.objects.companies.read
crm.objects.companies.write
crm.objects.contacts.read
crm.objects.contacts.write
crm.objects.notes.write
crm.objects.tasks.write
```

5. Copy the private app token.

## Backend Environment

```bash
HUBSPOT_PRIVATE_APP_TOKEN=pat-...
```

## Current Scope

The adapter supports:

- upsert company,
- upsert contact,
- create note,
- create task.

HubSpot remains optional. Errors in CRM sync should not block draft generation.
