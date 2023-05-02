import ts from "typescript";

export function tryGetDecorators(
  node: ts.Node
): readonly ts.Decorator[] | undefined {
  return ts.canHaveDecorators(node) ? ts.getDecorators(node) : undefined;
}
