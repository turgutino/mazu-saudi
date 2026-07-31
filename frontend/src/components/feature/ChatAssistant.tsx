import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { ChatMessage } from '@/mocks/chatResponses';
import { SUGGESTED_QUESTIONS, GENERAL_QUESTIONS, generateResponse, generateGeneralResponse } from '@/mocks/chatResponses';
import { sendChatMessage } from '@/services/chatService';
import { useChatContext } from '@/hooks/useChatContext';

export default function ChatAssistant() {
  const context = useChatContext();
  const navigate = useNavigate();

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const initialMessageSent = useRef(false);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Reset welcome message when context changes
  useEffect(() => {
    if (isOpen) {
      setMessages([]);
      initialMessageSent.current = false;
    }
  }, [context?.predictionId, isOpen]);

  // Send initial welcome message when opened
  useEffect(() => {
    if (isOpen && !initialMessageSent.current) {
      initialMessageSent.current = true;
      const welcomeMsg = context
        ? generateResponse('你好', context)
        : generateGeneralResponse('你好');
      setMessages([{
        role: 'agent',
        content: welcomeMsg,
        timestamp: Date.now(),
      }]);
    }
  }, [isOpen, context]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsTyping(true);

    try {
      const result = await sendChatMessage(text.trim(), messages, context);

      const agentMsg: ChatMessage = {
        role: 'agent',
        content: result.content,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch {
      // Ultimate fallback — should never reach here since service has built-in fallback
      const fallbackContent = context
        ? generateResponse(text.trim(), context)
        : generateGeneralResponse(text.trim());
      const agentMsg: ChatMessage = {
        role: 'agent',
        content: fallbackContent,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } finally {
      setIsTyping(false);
    }
  }, [context, messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const formatContent = (content: string) => {
    return content.split('\n').map((line, i) => {
      let formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-foreground-900">$1</strong>');
      if (formatted.trim() === '') {
        return <div key={i} className="h-2"></div>;
      }
      return (
        <p
          key={i}
          className="text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: formatted }}
        ></p>
      );
    });
  };

  const questions = context ? SUGGESTED_QUESTIONS : GENERAL_QUESTIONS;
  const headerLabel = context
    ? `${context.regionName} · ${context.hazardLabel}`
    : '通用助手';

  const resetConversation = () => {
    setMessages([]);
    initialMessageSent.current = false;
    const welcomeMsg = context
      ? generateResponse('你好', context)
      : generateGeneralResponse('你好');
    setMessages([{ role: 'agent', content: welcomeMsg, timestamp: Date.now() }]);
  };

  const goToWorkspace = () => {
    navigate('/workspace');
  };

  return (
    <>
      {/* Toggle button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary-500 text-white flex items-center justify-center cursor-pointer hover:bg-primary-600 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105"
          aria-label="打开预测助手"
        >
          <i className="ri-chat-3-line text-xl"></i>
        </button>
      )}

      {/* Chat panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-[380px] max-w-[calc(100vw-3rem)] bg-background-50 border border-background-200/70 rounded-xl shadow-lg flex flex-col overflow-hidden transition-all duration-300 animate-[slideUp_0.25s_ease-out]"
          style={{ maxHeight: '560px', height: '520px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-background-200/70 bg-background-100">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                <i className="ri-robot-line text-primary-600"></i>
              </div>
              <div>
                <p className="text-sm font-medium text-foreground-900">预测智能体</p>
                <p className="text-[11px] text-foreground-500">{headerLabel}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={resetConversation}
                className="p-1.5 rounded-md hover:bg-background-200 cursor-pointer text-foreground-400"
                title="清除对话"
              >
                <i className="ri-delete-back-2-line text-sm"></i>
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-md hover:bg-background-200 cursor-pointer text-foreground-400"
              >
                <i className="ri-close-line text-sm"></i>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'agent' && (
                  <div className="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mr-2 mt-1">
                    <i className="ri-robot-line text-primary-600 text-xs"></i>
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-xl px-3.5 py-2.5 ${
                    msg.role === 'user'
                      ? 'bg-primary-500 text-white'
                      : 'bg-background-100 border border-background-200/50'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <p className="text-sm">{msg.content}</p>
                  ) : (
                    <div className="text-foreground-700">
                      {formatContent(msg.content)}
                    </div>
                  )}
                  <p className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-white/60' : 'text-foreground-400'}`}>
                    {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-6 h-6 rounded-full bg-foreground-200 flex items-center justify-center flex-shrink-0 ml-2 mt-1">
                    <i className="ri-user-line text-foreground-600 text-xs"></i>
                  </div>
                )}
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mr-2 mt-1">
                  <i className="ri-robot-line text-primary-600 text-xs"></i>
                </div>
                <div className="bg-background-100 border border-background-200/50 rounded-xl px-4 py-3">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-foreground-300 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-2 h-2 rounded-full bg-foreground-300 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-2 h-2 rounded-full bg-foreground-300 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef}></div>
          </div>

          {/* Suggested questions */}
          {messages.length <= 1 && (
            <div className="px-4 py-2 border-t border-background-200/50 flex flex-wrap gap-1.5">
              {questions.map((q) => (
                <button
                  key={q.label}
                  onClick={() => sendMessage(q.label)}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-background-100 border border-background-200/70 text-xs text-foreground-600 hover:bg-background-200 hover:text-foreground-800 cursor-pointer transition-colors whitespace-nowrap"
                >
                  <i className={`${q.icon} text-[10px]`}></i>
                  {q.label}
                </button>
              ))}
              {!context && (
                <button
                  onClick={goToWorkspace}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-primary-100 border border-primary-200 text-xs text-primary-700 hover:bg-primary-200 cursor-pointer transition-colors whitespace-nowrap"
                >
                  <i className="ri-rocket-line text-[10px]"></i>
                  前往工作台
                </button>
              )}
            </div>
          )}

          {/* Input area */}
          <div className="border-t border-background-200/70 px-4 py-3 bg-background-50">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入问题，按 Enter 发送..."
                rows={1}
                className="flex-1 resize-none bg-background-100 border border-background-200/70 rounded-lg px-3 py-2 text-sm text-foreground-900 placeholder:text-foreground-400 focus:outline-none focus:border-primary-300 max-h-24"
              />
              <button
                onClick={() => sendMessage(inputValue)}
                disabled={!inputValue.trim() || isTyping}
                className="w-9 h-9 rounded-lg bg-primary-500 text-white flex items-center justify-center cursor-pointer hover:bg-primary-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
              >
                <i className="ri-send-plane-fill text-sm"></i>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
