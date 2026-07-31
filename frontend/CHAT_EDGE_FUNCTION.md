# chat-prediction Edge Function（LiteLLM 代理）

复制以下内容到 Supabase Dashboard → Edge Functions → 新建 Function（slug: `chat-prediction`，JWT 验证开启）。

## 前置 Secrets（Supabase Dashboard → Settings → Edge Function Secrets）

| Secret 名称 | 说明 |
|---|---|
| `LITELLM_API_KEY` | LiteLLM API key |
| `LITELLM_BASE_URL` | LiteLLM endpoint（如 `https://llm.your-domain.com`） |
| `LITELLM_MODEL` | 模型名（如 `gpt-4o` / `claude-sonnet-4-20250514`） |

## 前端调用方式

```typescript
const { data } = await supabase.functions.invoke('chat-prediction', {
  body: { messages: [...], context: {...} },
});
// data.content → LLM 返回的文本
```

## 完整代码

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const LITELLM_API_KEY = Deno.env.get("LITELLM_API_KEY") ?? "";
const LITELLM_BASE_URL = Deno.env.get("LITELLM_BASE_URL") ?? "https://api.openai.com/v1";
const LITELLM_MODEL = Deno.env.get("LITELLM_MODEL") ?? "gpt-4o-mini";

interface ChatMessage {
  role: string;
  content: string;
}

interface RequestBody {
  messages: ChatMessage[];
  context?: Record<string, unknown> | null;
}

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const body: RequestBody = await req.json();
    const { messages } = body;

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return new Response(
        JSON.stringify({ error: "messages array is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    if (!LITELLM_API_KEY) {
      return new Response(
        JSON.stringify({ error: "LITELLM_API_KEY not configured" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const llmResponse = await fetch(`${LITELLM_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${LITELLM_API_KEY}`,
      },
      body: JSON.stringify({
        model: LITELLM_MODEL,
        messages,
        temperature: 0.4,
        max_tokens: 800,
      }),
    });

    if (!llmResponse.ok) {
      const errorText = await llmResponse.text();
      console.error("LiteLLM error:", llmResponse.status, errorText);
      return new Response(
        JSON.stringify({ error: `LiteLLM returned ${llmResponse.status}` }),
        { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const llmData = await llmResponse.json();
    const content = llmData.choices?.[0]?.message?.content ?? "";

    return new Response(
      JSON.stringify({ content }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (err) {
    console.error("chat-prediction error:", err);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }
});
```