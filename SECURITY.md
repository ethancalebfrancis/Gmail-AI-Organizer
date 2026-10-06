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

## API keys

Keep `OPENAI_API_KEY` in the local `.env` file only. Do not place the key in source code, Git commits, screenshots, issue text, shell transcripts, or launchd's global environment.

If a key appears in terminal output or any shared artifact, revoke it and create a replacement before continuing.

The macOS service does not need the API key embedded in its plist; the application reads `.env` from the repository working directory.

## Gmail deletion safety

The organizer intentionally quarantines deletion candidates before moving them to Gmail Trash and re-checks starred, Inbox-restored, protected-category, and protected-label state before cleanup.

The quarantine duration is configurable locally. Shortening it changes the recovery window but does not bypass the protected-category rules or cleanup safety checks.
