import ts from "typescript";

/**
 * Visit a node with the given visitor and return a transformed copy.
 */
export function visit<T extends ts.Node>(
  node: T,
  visitor: Visitor,
  context: ts.TransformationContext
): T {
  return visitor.visitIteration(node, context);
}

/**
 * Abstract base class for visitors, which processes certain nodes specially to allow insertion
 * of other nodes before them.
 */
export abstract class Visitor {
  /**
   * Visit a class declaration, returning at least the transformed declaration and optionally other
   * nodes to insert before the declaration.
   */
  abstract visitClassDeclaration(
    node: ts.ClassDeclaration
  ): ts.ClassDeclaration;

  /**
   * Visit an import declaration, returning at least the transformed declaration
   */
  visitImportDeclaration(node: ts.ImportDeclaration): ts.ImportDeclaration {
    return node;
  }

  /**
   * @internal
   */
  visitIteration<T extends ts.Node>(
    node: T,
    context: ts.TransformationContext
  ): T {
    node = ts.visitEachChild(
      node,
      (child) => this.visitIteration(child, context),
      context
    );

    if (ts.isClassDeclaration(node)) {
      return this.visitClassDeclaration(node) as typeof node;
    } else if (ts.isImportDeclaration(node)) {
      return this.visitImportDeclaration(node) as typeof node;
    } else {
      return node;
    }
  }
}
