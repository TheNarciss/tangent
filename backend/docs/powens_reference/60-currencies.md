# Page Not Found

The URL `overview/currencies` does not exist. This page may have been moved, renamed, or deleted.

## Suggested Pages

You may be looking for one of the following:
- [Authentication](https://docs.powens.com/api-reference/overview/authentication.md)
- [Errors](https://docs.powens.com/api-reference/overview/errors.md)
- [Webview](https://docs.powens.com/api-reference/overview/webview.md)
- [Currencies](https://docs.powens.com/api-reference/products/data-aggregation/currencies.md)
- [API design](https://docs.powens.com/api-reference/overview/api-design.md)

## How to find the correct page

If the exact page cannot be found, you can still retrieve the information using the documentation query interface.

### Option 1 — Ask a question (recommended)

Perform an HTTP GET request on the documentation index with the `ask` parameter:

```
GET https://docs.powens.com/api-reference/overview/authentication.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

### Option 2 — Browse the documentation index

Full index: https://docs.powens.com/api-reference/sitemap.md

Use this to discover valid page paths or navigate the documentation structure.

### Option 3 — Retrieve the full documentation corpus

Full export: https://docs.powens.com/api-reference/llms-full.txt

Use this to access all content at once and perform your own parsing or retrieval. It will be more expensive.

## Tips for requesting documentation

Prefer `.md` URLs for structured content, append `.md` to URLs (e.g., `/api-reference/overview/authentication.md`).

You may also use `Accept: text/markdown` header for content negotiation.
