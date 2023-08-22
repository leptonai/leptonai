import ts from "typescript";
import {
  Decorator,
  NamedClassDeclaration,
  Import,
  TypeValueReference,
  TypeValueReferenceKind,
} from "../reflection/host";
import {
  ExternalExpr,
  OutputExpression,
  ReadPropExpr,
  WrappedNodeExpr,
} from "../decorators/expression";
import { Identifiers } from "./identifiers";

/**
 * Convert a `TypeValueReference` to an `OutputExpression` which refers to the type as a value.
 *
 * Local references are converted to a `WrappedNodeExpr` of the TypeScript expression, and non-local
 * references are converted to an `ExternalExpr`. Note that this is only valid in the context of the
 * file in which the `TypeValueReference` originated.
 */
export function valueReferenceToExpression(
  valueRef: TypeValueReference
): OutputExpression | null {
  if (valueRef.kind === TypeValueReferenceKind.UNAVAILABLE) {
    return null;
  } else if (valueRef.kind === TypeValueReferenceKind.LOCAL) {
    return new WrappedNodeExpr(valueRef.expression);
  } else {
    let importExpr: OutputExpression = new ExternalExpr(valueRef.importedName);
    if (valueRef.nestedPath !== null) {
      for (const property of valueRef.nestedPath) {
        importExpr = new ReadPropExpr(importExpr, property);
      }
    }
    return importExpr;
  }
}
export function isTargetDecorator(
  decorator: Decorator
): decorator is Decorator & { import: Import } {
  return (
    decorator.import !== null && decorator.import.from === Identifiers.module
  );
}

export function findTargetDecorator(
  decorators: Decorator[],
  name: string
): Decorator | undefined {
  return decorators.find(
    (decorator) =>
      isTargetDecorator(decorator) && decorator.import.name === name
  );
}

export function isNamedClassDeclaration(
  node: ts.Node
): node is NamedClassDeclaration {
  return (
    ts.isClassDeclaration(node) &&
    node.name !== undefined &&
    ts.isIdentifier(node.name)
  );
}
