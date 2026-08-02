export interface GraphDimensions {
  width: number;
  height: number;
}

export interface GraphViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function createFittedGraphViewBox(
  dimensions: GraphDimensions,
  padding = 50,
): GraphViewBox {
  const safePadding = Math.max(0, padding);
  return {
    x: safePadding === 0 ? 0 : -safePadding,
    y: safePadding === 0 ? 0 : -safePadding,
    w: Math.max(1, dimensions.width) + safePadding * 2,
    h: Math.max(1, dimensions.height) + safePadding * 2,
  };
}

export function createNodeLabelPreview(
  label: string,
  maxCharsPerLine = 18,
  maxLines = 3,
  fallbackLabel = '未命名节点',
): string[] {
  const lineLimit = Math.max(1, Math.floor(maxCharsPerLine));
  const visibleLineLimit = Math.max(1, Math.floor(maxLines));
  const sourceLines = label.split('\n').map((line) => line.trim()).filter(Boolean);
  const lines = sourceLines.length > 0 ? sourceLines : [fallbackLabel];
  const preview = lines.slice(0, visibleLineLimit).map((line) => {
    const characters = Array.from(line);
    return characters.length > lineLimit
      ? `${characters.slice(0, lineLimit - 1).join('')}…`
      : line;
  });

  if (lines.length > visibleLineLimit) {
    const lastIndex = preview.length - 1;
    const lastLine = Array.from(preview[lastIndex].replace(/…$/, ''));
    preview[lastIndex] = `${lastLine.slice(0, lineLimit - 1).join('')}…`;
  }

  return preview;
}
