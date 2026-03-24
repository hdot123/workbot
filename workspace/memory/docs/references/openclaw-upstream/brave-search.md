> ## Documentation Index
> Fetch the complete documentation index at: https://docs.openclaw.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Brave Search

# Brave Search API

OpenClaw uses Brave Search as the default provider for `web_search`.

## Get an API key

1. Create a Brave Search API account at [https://brave.com/search/api/](https://brave.com/search/api/)
2. In the dashboard, choose the **Data for Search** plan and generate an API key.
3. Store the key in config (recommended) or set `BRAVE_API_KEY` in the Gateway environment.

## Config example

```json5  theme={"theme":{"light":"min-light","dark":"min-dark"}}
{
  tools: {
    web: {
      search: {
        provider: "brave",
        apiKey: "BRAVE_API_KEY_HERE",
        maxResults: 5,
        timeoutSeconds: 30,
      },
    },
  },
}
```

## Notes

* The Data for AI plan is **not** compatible with `web_search`.
* Brave provides paid plans; check the Brave API portal for current limits.
* Brave Terms include restrictions on some AI-related uses of Search Results. Review the Brave Terms of Service and confirm your intended use is compliant. For legal questions, consult your counsel.

See [Web tools](/tools/web) for the full web\_search configuration.
