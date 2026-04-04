# Blog Publishing Platform Port Design

**Goal**

Port the already-validated multi-platform publishing core from `blog-writer-mcp` into `blog-writer-blog` without disturbing unrelated dashboard, n8n, or collector work. The port should add WordPress publishing, Naver unattended publishing, representative image preparation for Naver, and platform selection controls for the standalone blog CLI and existing publish flows.

**Scope**

- Add `WordPress` publishing through the REST API with Application Password auth.
- Add `Naver` unattended publishing through Playwright with a persistent Chrome profile.
- Add representative image resolution for Naver using `existing image -> BananaPro -> OpenAI`.
- Keep Blogger as the default publishing path.
- Extend `bw publish` so callers can choose `blogger | wordpress | both | naver | all`.
- Preserve existing manual review behavior and make approval honor the originally requested platform set.
- Update env/config/docs/tests for the new publishing platforms.

**Out of Scope**

- New dashboard UI for platform selection.
- Deep refactors of existing writer, collector, n8n, or dashboard systems.
- Replacing the current Blogger publishing implementation.

**Architecture**

`bots/publisher_bot.py` remains the public publishing entrypoint for `blog-writer-blog`. It will be extended into a lightweight router that keeps existing Blogger behavior and delegates to `bots/wp_publisher_bot.py` and `bots/naver_publisher_bot.py` for non-Blogger platforms.

The Naver publisher will reuse a focused `bots/image_bot.py` helper so unattended publishing can always try to prepare one representative image. Approval flows will reuse the same router by persisting the requested platform set into pending-review payloads.

**Success Criteria**

- `publish(article, platform="wordpress")` publishes to WordPress successfully.
- `publish(article, platform="both")` publishes to Blogger and WordPress.
- `publish(article, platform="all")` publishes to Blogger, WordPress, and Naver.
- `bw publish --platform ...` routes to the requested platforms.
- Existing Blogger publishing behavior remains the default.
- New and existing touched tests pass.
