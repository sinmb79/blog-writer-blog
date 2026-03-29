# Blog Writer Blog

Standalone blog-only app extracted from the original `blog-writer` workspace.

## Included

- Topic collection
- Article writing
- Pending review approval and rejection
- Blogger publishing
- Blog-only dashboard

## Not Included

- Shorts
- Novels
- SNS distribution
- Assist mode

## Quick Start

1. Create a virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env` and fill in Blogger and API settings.
4. Start the dashboard backend:

```powershell
python -m uvicorn dashboard.backend.server:app --port 8080 --reload
```

5. Start the frontend:

```powershell
cd dashboard/frontend
npm install
npm run dev
```

6. Use the CLI:

```powershell
bw --help
```

## Korean Beginner Guide

- See [docs/BEGINNER_GUIDE_KO.md](docs/BEGINNER_GUIDE_KO.md) for a detailed beginner-friendly Korean guide.
