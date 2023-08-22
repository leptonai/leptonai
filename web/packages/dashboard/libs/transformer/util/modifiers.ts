import ts from "typescript";

export function tryGetModifiers(
  node: ts.Node
): readonly ts.Modifier[] | undefined {
  return ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined;
}
