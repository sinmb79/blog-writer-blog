# Blog Writer Blog

Standalone blog automation for collecting topics, drafting articles with AI, and publishing to Blogger, WordPress, and Naver.

## What is included

- Topic collection from RSS, Hacker News, and GitHub Trending
- AI draft generation
- Manual review queue
- Blogger publishing by default
- WordPress publishing through the REST API
- Naver unattended publishing through Playwright and a persistent Chrome profile

## Publish targets

Use the CLI to select where each draft should go:

```powershell
bw publish --platform blogger
bw publish --platform wordpress
bw publish --platform both
bw publish --platform naver
bw publish --platform all
```

## Naver unattended publishing

1. Create a dedicated Naver account and Chrome profile.
2. Log in once with that profile.
3. Set `NAVER_CHROME_PROFILE_DIR` in `.env`.
4. Install Playwright Chromium:

```bash
python -m playwright install chromium
```

Representative image fallback order:

```text
existing image_path -> BananaPro -> OpenAI
```
