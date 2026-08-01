export interface ChatTextSegment {
  text: string;
  strong: boolean;
}

/** Splits the one supported markdown construct without interpreting HTML. */
export function splitChatText(line: string): ChatTextSegment[] {
  return line.split(/(\*\*.*?\*\*)/g).map((part) => ({
    text: part.startsWith('**') && part.endsWith('**') ? part.slice(2, -2) : part,
    strong: part.startsWith('**') && part.endsWith('**'),
  }));
}
