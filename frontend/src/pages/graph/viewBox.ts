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
