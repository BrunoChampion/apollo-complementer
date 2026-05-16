# Email Deliverability Setup

This guide is for NYVEX cold outbound domains and inboxes.

## Recommended Domain Strategy

Do not use the primary domain `nyvex.dev` for early cold outbound. Keep it for clients, replies, invoices, product access, and reputation-sensitive communication.

Use 2-3 secondary domains at first, for example:

```text
getnyvex.com
trynyvex.com
nyvexai.com
```

Avoid deceptive typo domains that look like impersonation. Each outbound domain should redirect its website traffic to the primary NYVEX website and should have its own email authentication records.

## DNS Records For Google Workspace

Use these when the sending inboxes are hosted in Google Workspace.

### MX

At the root of the domain, configure Google Workspace MX records:

```text
Host: @
Type: MX
Priority: 1
Value: smtp.google.com
TTL: auto or 3600
```

If your Google Workspace setup screen gives you the older 5-record MX set, use the exact values Google shows in Admin Console.

### SPF

Add one TXT record at the root:

```text
Host: @
Type: TXT
Value: v=spf1 include:_spf.google.com ~all
TTL: auto or 3600
```

Important: keep one SPF record per domain. If another sender is added later, merge it into this same TXT record instead of creating another SPF record.

### DKIM

Generate DKIM in Google Admin Console:

```text
Apps -> Google Workspace -> Gmail -> Authenticate email
```

Use a 2048-bit DKIM key when available. Google will give you:

```text
Host: google._domainkey
Type: TXT
Value: v=DKIM1; k=rsa; p=...
```

Add that TXT record in DNS, wait for propagation, then return to Google Admin and click `Start authentication`.

### DMARC

Start with monitoring:

```text
Host: _dmarc
Type: TXT
Value: v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com; adkim=s; aspf=s; fo=1
TTL: auto or 3600
```

After 2-4 weeks of clean reports, move gradually:

```text
v=DMARC1; p=quarantine; pct=25; rua=mailto:dmarc@yourdomain.com; adkim=s; aspf=s; fo=1
```

Then increase `pct` toward 100. Use `p=reject` only once you know all legitimate senders pass SPF/DKIM alignment.

## Current Provider Requirements

As of May 2026:

- Gmail requires all senders to use SPF or DKIM, TLS, valid forward/reverse DNS, RFC 5322 formatting, and low spam rates. Bulk senders above 5,000 messages/day must use SPF, DKIM, DMARC, aligned From domains, and one-click unsubscribe for marketing/subscribed messages.
- Microsoft Outlook.com consumer mail applies SPF, DKIM, and DMARC requirements for domains sending more than 5,000 messages/day to Microsoft consumer mailboxes.
- Yahoo requires strong sender authentication and one-click unsubscribe for bulk senders; Yahoo does not publish a fixed numeric bulk threshold.

## Cold Outbound Operating Rules

For a new NYVEX outbound setup:

- Start with 2-3 domains and 1-2 inboxes per domain.
- Keep volume low at the beginning; do not create sudden spikes.
- Prefer plain text or very light HTML.
- Do not use misleading `Re:` or `Fwd:` subjects.
- Do not use link-heavy first emails.
- Avoid open tracking at the start if deliverability is weak.
- Include a simple opt-out line for cold commercial email.
- Stop mailing hard bounces immediately.
- Suppress anyone who opts out.
- Monitor Google Postmaster Tools for the main domain once volume exists.
- Keep the primary domain out of cold outbound unless the relationship is already warm.

## Domain Buying

For low-cost alternate domains:

- Cloudflare Registrar is usually the best long-term cost if the TLD is supported because it sells domains at registry cost with no markup.
- Porkbun is often very cheap and transparent for first-year and renewals.
- Namecheap can be cheap for first-year promos, but check renewal price before buying.

Prefer normal, trusted TLDs like `.com` when available. Avoid spam-associated cheap TLDs for outbound.

## What Revenue Ops Copilot Does Not Do

This project does not manage:

- inbox warmup,
- inbox rotation,
- sending throttles,
- bounce classification,
- unsubscribe headers,
- suppression lists,
- reply detection,
- domain reputation monitoring.

It currently creates Gmail drafts for human review. Use it upstream for research, fit scoring, message drafting, evidence, and approval.
