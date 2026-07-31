import type { ChatMessage, ChatContext } from '@/mocks/chatResponses';
import { generateResponse, generateGeneralResponse } from '@/mocks/chatResponses';

// ============================================================
// 当 Supabase 接入 LiteLLM 后，替换下面的 stub 即可。
// 前端无需改动，只需部署 supabase/functions/chat-prediction。
// ============================================================

let supabaseClient: any = null;

async function getSupabase() {
  if (supabaseClient) return supabaseClient;

  const supabaseUrl = import.meta.env.VITE_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = import.meta.env.VITE_PUBLIC_SUPABASE_ANON_KEY;

  if (supabaseUrl && supabaseAnonKey) {
    try {
      const { createClient } = await import('@supabase/supabase-js');
      supabaseClient = createClient(supabaseUrl, supabaseAnonKey);
      return supabaseClient;
    } catch {
      return null;
    }
  }

  return null;
}

export interface LLMRequest {
  messages: { role: string; content: string }[];
  context?: ChatContext | null;
  systemPrompt?: string;
}

export interface LLMResponse {
  content: string;
  source: 'llm' | 'keyword-fallback';
}

const SYSTEM_PROMPT_PREDICTION = `You are a weather prediction intelligence agent for an extreme weather forecasting system.
Your role is to explain prediction results with rigor — never fabricate probabilities, risk levels, or data.

Core principles:
1. Probabilities come from trained models; you explain them, you don't invent them.
2. Distinguish between model reasoning (SHAP feature contributions) and physical mechanisms (expert knowledge).
3. When uncertain, acknowledge it — don't hide model version, data source, or uncertainty bounds.
4. All responses should reference the prediction context provided.
5. Use the user's language (Chinese or English) in responses.
6. Keep responses concise but complete — 150-300 words unless the user asks for more detail.`;

const SYSTEM_PROMPT_GENERAL = `You are a weather prediction intelligence agent for an extreme weather forecasting system.
You help users understand the system's capabilities, navigate predictions, and interpret results.

Core principles:
1. Never fabricate any prediction numbers — all quantitative results come from actual model runs.
2. Guide users to the appropriate page for actions (workspace for new predictions, dashboard for overview).
3. Explain the architecture: data → model → risk assessment → explanation → knowledge graph.
4. Use the user's language in responses.
5. Keep responses helpful and concise.`;

/**
 * Call the LLM via Supabase Edge Function.
 * Falls back to keyword matching if Supabase is not connected or the call fails.
 */
export async function sendChatMessage(
  userMessage: string,
  history: ChatMessage[],
  context: ChatContext | null,
): Promise<LLMResponse> {
  const supabase = await getSupabase();

  // Build conversation history for LLM
  const messages = [
    { role: 'system', content: context ? SYSTEM_PROMPT_PREDICTION : SYSTEM_PROMPT_GENERAL },
  ];

  // Add context as a system message if available
  if (context) {
    messages.push({
      role: 'system',
      content: `Current prediction context:
- Region: ${context.regionName}
- Hazard: ${context.hazardLabel}
- Risk level: ${context.riskLevel}
- Calibrated probability: ${(context.calibratedProbability * 100).toFixed(0)}%
- Uncertainty: ±${(context.uncertainty * 100).toFixed(0)}%
- Model: ${context.modelName} ${context.modelVersion}
- Lead time: ${context.leadTimeHours}h
- Top features: ${context.featureNames.slice(0, 5).join(', ')}
- Triggered rules: ${context.triggeredRuleCount}/${context.totalRuleCount}
- Physical mechanisms: ${context.mechanismCount} paths
- Similar historical events: ${context.similarEventCount}
- Prediction ID: ${context.predictionId}`,
    });
  }

  // Add recent conversation history (last 6 messages)
  for (const msg of history.slice(-6)) {
    messages.push({ role: msg.role === 'user' ? 'user' : 'assistant', content: msg.content });
  }

  // Add the current user message
  messages.push({ role: 'user', content: userMessage });

  // Try LLM if Supabase is available
  if (supabase) {
    try {
      const { data, error } = await supabase.functions.invoke('chat-prediction', {
        body: { messages, context: context ? { ...context } : null },
      });

      if (!error && data?.content) {
        return { content: data.content, source: 'llm' };
      }
    } catch {
      // LLM call failed — fall through to keyword matching
    }
  }

  // Keyword fallback
  const fallbackContent = context
    ? generateResponse(userMessage, context)
    : generateGeneralResponse(userMessage);

  return { content: fallbackContent, source: 'keyword-fallback' };
}