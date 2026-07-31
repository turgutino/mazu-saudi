/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { ChatContext } from '@/mocks/chatResponses';

interface ChatContextState {
  context: ChatContext | null;
  setContext: (ctx: ChatContext | null) => void;
}

const ChatCtx = createContext<ChatContextState>({
  context: null,
  setContext: () => {},
});

export function ChatContextProvider({ children }: { children: ReactNode }) {
  const [context, setContext] = useState<ChatContext | null>(null);

  const updateContext = useCallback((ctx: ChatContext | null) => {
    setContext(ctx);
  }, []);

  return (
    <ChatCtx.Provider value={{ context, setContext: updateContext }}>
      {children}
    </ChatCtx.Provider>
  );
}

export function useChatContext() {
  return useContext(ChatCtx).context;
}

export function useSetChatContext() {
  return useContext(ChatCtx).setContext;
}
