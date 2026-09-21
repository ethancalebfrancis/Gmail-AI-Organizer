# Security

This application operates on a real Gmail account and uses local OAuth/API credentials.

Never commit or publish:

- `.env`
- `credentials.json`
- `token.json`
- `emails.db`
- `backlog_cache.db`
- logs containing mailbox metadata

The repository `.gitignore` excludes these files by default. Use `.env.example` for public configuration examples.

The organizer intentionally quarantines deletion candidates before moving them to Gmail Trash and re-checks starred, Inbox-restored, protected-category, and protected-label state before cleanup.
