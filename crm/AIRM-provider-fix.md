# AIRM provider swap — scripted fix (ready to apply)

**Target:** n8n workflow `Anagata AIRM - Multi-Agent Sales` (id `Bi59ePiaaat3XIHj`)
**When:** after owner flips "Available in MCP" on that workflow card / settings.

## Problem
AIRM's LLM nodes point at "Ollama account" credential → Ollama Cloud — weekly limit
exhausted → WhatsApp auto-reply sends the "model provider is rate-limiting" fallback.

## Fix (per node)
For every `@n8n/n8n-nodes-langchain.lmChatOllama` node in the workflow:
- type → `@n8n/n8n-nodes-langchain.lmChatOpenAi`
- credentials → `{ "openAiApi": { "id": "NexReT9zk3GuX1sO", "name": "FreeLLM" } }`
  (FreeLLM credential already exists in n8n, id confirmed via list_credentials)
- parameters → `{ "model": "deepseek-v4-flash" }`
- ensure baseURL lives in the FreeLLM credential (https://freellm.anagataitsolutions.in/v1)

Apply via MCP `update_workflow` (backup saved: `secrets/airm_workflow_backup.json`).
Verify with a `test_workflow` run or a 1:1 chat to the owner's number.

## Also noted
- Second candidate set: `CRM - Marketing Carousel Demo`, `CRM - Marketing Animation Video Demo`
  use "Ollama account" too (glm-5.2) — same swap if they must keep working.
- Local Ollama on VPS (11434) NOT reachable → no zero-new-credential local fallback.