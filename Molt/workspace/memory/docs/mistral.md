> ## Documentation Index
> Fetch the complete documentation index at: https://docs.openclaw.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Mistral

# Mistral

OpenClaw supports Mistral for both text/image model routing (`mistral/...`) and
audio transcription via Voxtral in media understanding.
Mistral can also be used for memory embeddings (`memorySearch.provider = "mistral"`).

## CLI setup

```bash  theme={"theme":{"light":"min-light","dark":"min-dark"}}
openclaw onboard --auth-choice mistral-api-key
# or non-interactive
openclaw onboard --mistral-api-key "$MISTRAL_API_KEY"
```

## Config snippet (LLM provider)

```json5  theme={"theme":{"light":"min-light","dark":"min-dark"}}
{
  env: { MISTRAL_API_KEY: "sk-..." },
  agents: { defaults: { model: { primary: "mistral/mistral-large-latest" } } },
}
```

## Config snippet (audio transcription with Voxtral)

```json5  theme={"theme":{"light":"min-light","dark":"min-dark"}}
{
  tools: {
    media: {
      audio: {
        enabled: true,
        models: [{ provider: "mistral", model: "voxtral-mini-latest" }],
      },
    },
  },
}
```

## Notes

* Mistral auth uses `MISTRAL_API_KEY`.
* Provider base URL defaults to `https://api.mistral.ai/v1`.
* Onboarding default model is `mistral/mistral-large-latest`.
* Media-understanding default audio model for Mistral is `voxtral-mini-latest`.
* Media transcription path uses `/v1/audio/transcriptions`.
* Memory embeddings path uses `/v1/embeddings` (default model: `mistral-embed`).
