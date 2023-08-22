import ts from "typescript";

import {
  NamedClassDeclaration,
  ClassMember,
  ClassMemberKind,
  CtorParameter,
  Decorator,
  Import,
  isDecoratorIdentifier,
} from "./host";
import { typeToValue } from "./type_to_value";
import { tryGetDecorators } from "../util/decorators";

/**
 * Abstracts reflection operations on a TypeScript AST.
 *
 * Depending on the format of the code being interpreted, different concepts are represented
 * with different syntactical structures. The `ReflectionHost` abstracts over those differences and
 * presents a single API by which the compiler can query specific information about the AST.
 *
 * All operations on the `ReflectionHost` require the use of TypeScript `ts.Node`s with binding
 * information already available (that is, nodes that come from a `ts.Program` that has been
 * type-checked, and are not synthetically created).
 */

export class TypeScriptReflectionHost {
  constructor(protected checker: ts.TypeChecker) {}

  /**
   * Examine a declaration (for example, of a class or function) and return metadata about any
   * decorators present on the declaration.
   *
   * @param declaration a TypeScript `ts.Declaration` node representing the class or function over
   * which to reflect. For example, if the intent is to reflect the decorators of a class and the
   * source is in ES6 format, this will be a `ts.ClassDeclaration` node. If the source is in ES5
   * format, this might be a `ts.VariableDeclaration` as classes in ES5 are represented as the
   * result of an IIFE execution.
   *
   * @returns an array of `Decorator` metadata if decorators are present on the declaration, or
   * `null` if either no decorators were present or if the declaration is not of a decoratable type.
   */
  getDecoratorsOfDeclaration(declaration: ts.Declaration): Decorator[] | null {
    const decorators = tryGetDecorators(declaration);
    if (decorators === undefined || decorators.length === 0) {
      return null;
    }
    return decorators
      .map((decorator) => this._reflectDecorator(decorator))
      .filter((dec): dec is Decorator => dec !== null);
  }

  /**
   * Examine a declaration which should be of a class, and return metadata about the members of the
   * class.
   *
   * @param clazz a `ClassDeclaration` representing the class over which to reflect.
   *
   * @returns an array of `ClassMember` metadata representing the members of the class.
   *
   * @throws if `declaration` does not resolve to a class declaration.
   */
  getMembersOfClass(clazz: NamedClassDeclaration): ClassMember[] {
    return clazz.members
      .map((member) => this._reflectMember(member))
      .filter((member): member is ClassMember => member !== null);
  }

  /**
   * Reflect over the constructor of a class and return metadata about its parameters.
   *
   * This method only looks at the constructor of a class directly and not at any inherited
   * constructors.
   *
   * @param clazz a `ClassDeclaration` representing the class over which to reflect.
   *
   * @returns an array of `Parameter` metadata representing the parameters of the constructor, if
   * a constructor exists. If the constructor exists and has 0 parameters, this array will be empty.
   * If the class has no constructor, this method returns `null`.
   */
  getConstructorParameters(
    clazz: NamedClassDeclaration
  ): CtorParameter[] | null {
    const isDeclaration = clazz.getSourceFile().isDeclarationFile;
    // For non-declaration files, we want to find the constructor with a `body`. The constructors
    // without a `body` are overloads whereas we want the implementation since it's the one that'll
    // be executed and which can have decorators. For declaration files, we take the first one that
    // we get.
    const ctor = clazz.members.find(
      (member): member is ts.ConstructorDeclaration =>
        ts.isConstructorDeclaration(member) &&
        (isDeclaration || member.body !== undefined)
    );
    if (ctor === undefined) {
      return null;
    }

    return ctor.parameters.map((node) => {
      // The name of the parameter is easy.
      const name = parameterName(node.name);

      const decorators = this.getDecoratorsOfDeclaration(node);

      // It may or may not be possible to write an expression that refers to the value side of the
      // type named for the parameter.

      const originalTypeNode = node.type || null;
      let typeNode = originalTypeNode;

      // Check if we are dealing with a simple nullable union type e.g. `foo: Foo|null`
      // and extract the type. More complex union types e.g. `foo: Foo|Bar` are not supported.
      // We also don't need to support `foo: Foo|undefined` because DI injects `null` for
      // optional tokes that don't have providers.
      if (typeNode && ts.isUnionTypeNode(typeNode)) {
        const childTypeNodes = typeNode.types.filter(
          (childTypeNode) =>
            !(
              ts.isLiteralTypeNode(childTypeNode) &&
              childTypeNode.literal.kind === ts.SyntaxKind.NullKeyword
            )
        );

        if (childTypeNodes.length === 1) {
          typeNode = childTypeNodes[0];
        }
      }

      const typeValueReference = typeToValue(typeNode, this.checker);
      return {
        name,
        nameNode: node.name,
        typeValueReference,
        typeNode: originalTypeNode,
        decorators,
      };
    });
  }

  /**
   * Determine if an identifier was imported from another module and return `Import` metadata
   * describing its origin.
   *
   * @param id a TypeScript `ts.Identifier` to reflect.
   *
   * @returns metadata about the `Import` if the identifier was imported from another module, or
   * `null` if the identifier doesn't resolve to an import but instead is locally defined.
   */
  getImportOfIdentifier(id: ts.Identifier): Import | null {
    const directImport = this.getDirectImportOfIdentifier(id);
    if (directImport !== null) {
      return directImport;
    } else if (ts.isQualifiedName(id.parent) && id.parent.right === id) {
      return this.getImportOfNamespacedIdentifier(
        id,
        getQualifiedNameRoot(id.parent)
      );
    } else if (
      ts.isPropertyAccessExpression(id.parent) &&
      id.parent.name === id
    ) {
      return this.getImportOfNamespacedIdentifier(
        id,
        getFarLeftIdentifier(id.parent)
      );
    } else {
      return null;
    }
  }

  /**
   * Determines whether the given declaration, which should be a class, has a base class.
   *
   * @param clazz a `ClassDeclaration` representing the class over which to reflect.
   */
  hasBaseClass(clazz: NamedClassDeclaration): boolean {
    return this.getBaseClassExpression(clazz) !== null;
  }

  /**
   * Get an expression representing the base class (if any) of the given `clazz`.
   *
   * This expression is most commonly an Identifier, but is possible to inherit from a more dynamic
   * expression.
   *
   * @param clazz the class whose base we want to get.
   */
  getBaseClassExpression(clazz: NamedClassDeclaration): ts.Expression | null {
    if (
      !(ts.isClassDeclaration(clazz) || ts.isClassExpression(clazz)) ||
      clazz.heritageClauses === undefined
    ) {
      return null;
    }
    const extendsClause = clazz.heritageClauses.find(
      (clause) => clause.token === ts.SyntaxKind.ExtendsKeyword
    );
    if (extendsClause === undefined) {
      return null;
    }
    const extendsType = extendsClause.types[0];
    if (extendsType === undefined) {
      return null;
    }
    return extendsType.expression;
  }

  protected getDirectImportOfIdentifier(id: ts.Identifier): Import | null {
    const symbol = this.checker.getSymbolAtLocation(id);

    if (
      symbol === undefined ||
      symbol.declarations === undefined ||
      symbol.declarations.length !== 1
    ) {
      return null;
    }

    const decl = symbol.declarations[0];
    const importDecl = getContainingImportDeclaration(decl);

    // Ignore declarations that are defined locally (not imported).
    if (importDecl === null) {
      return null;
    }

    // The module specifier is guaranteed to be a string literal, so this should always pass.
    if (!ts.isStringLiteral(importDecl.moduleSpecifier)) {
      // Not allowed to happen in TypeScript ASTs.
      return null;
    }

    return {
      from: importDecl.moduleSpecifier.text,
      name: getExportedName(decl, id),
    };
  }

  /**
   * Try to get the import info for this identifier as though it is a namespaced import.
   *
   * For example, if the identifier is the `Directive` part of a qualified type chain like:
   *
   * ```
   * core.Directive
   * ```
   *
   * then it might be that `core` is a namespace import such as:
   *
   * ```
   * import * as core from 'tslib';
   * ```
   *
   * @param id the TypeScript identifier to find the import info for.
   * @param namespaceIdentifier
   * @returns The import info if this is a namespaced import or `null`.
   */
  protected getImportOfNamespacedIdentifier(
    id: ts.Identifier,
    namespaceIdentifier: ts.Identifier | null
  ): Import | null {
    if (namespaceIdentifier === null) {
      return null;
    }
    const namespaceSymbol =
      this.checker.getSymbolAtLocation(namespaceIdentifier);
    if (!namespaceSymbol || namespaceSymbol.declarations === undefined) {
      return null;
    }
    const declaration =
      namespaceSymbol.declarations.length === 1
        ? namespaceSymbol.declarations[0]
        : null;
    if (!declaration) {
      return null;
    }
    const namespaceDeclaration = ts.isNamespaceImport(declaration)
      ? declaration
      : null;
    if (!namespaceDeclaration) {
      return null;
    }

    const importDeclaration = namespaceDeclaration.parent.parent;
    if (!ts.isStringLiteral(importDeclaration.moduleSpecifier)) {
      // Should not happen as this would be invalid TypesScript
      return null;
    }

    return {
      from: importDeclaration.moduleSpecifier.text,
      name: id.text,
    };
  }

  private _reflectDecorator(node: ts.Decorator): Decorator | null {
    // Attempt to resolve the decorator expression into a reference to a concrete Identifier. The
    // expression may contain a call to a function which returns the decorator function, in which
    // case we want to return the arguments.
    let decoratorExpr: ts.Expression = node.expression;
    let args: ts.Expression[] | null = null;

    // Check for call expressions.
    if (ts.isCallExpression(decoratorExpr)) {
      args = Array.from(decoratorExpr.arguments);
      decoratorExpr = decoratorExpr.expression;
    }

    // The final resolved decorator should be a `ts.Identifier` - if it's not, then something is
    // wrong and the decorator can't be resolved statically.
    if (!isDecoratorIdentifier(decoratorExpr)) {
      return null;
    }

    const decoratorIdentifier = ts.isIdentifier(decoratorExpr)
      ? decoratorExpr
      : decoratorExpr.name;
    const importDecl = this.getImportOfIdentifier(decoratorIdentifier);

    return {
      name: decoratorIdentifier.text,
      import: importDecl,
      node,
      args,
    };
  }

  private _reflectMember(node: ts.ClassElement): ClassMember | null {
    let kind: ClassMemberKind | null = null;
    let value: ts.Expression | null = null;
    let name: string | null = null;
    let nameNode: ts.Identifier | ts.StringLiteral | null = null;

    if (ts.isPropertyDeclaration(node)) {
      kind = ClassMemberKind.Property;
      value = node.initializer || null;
    } else if (ts.isGetAccessorDeclaration(node)) {
      kind = ClassMemberKind.Getter;
    } else if (ts.isSetAccessorDeclaration(node)) {
      kind = ClassMemberKind.Setter;
    } else if (ts.isMethodDeclaration(node)) {
      kind = ClassMemberKind.Method;
    } else if (ts.isConstructorDeclaration(node)) {
      kind = ClassMemberKind.Constructor;
    } else {
      return null;
    }

    if (ts.isConstructorDeclaration(node)) {
      name = "constructor";
    } else if (ts.isIdentifier(node.name)) {
      name = node.name.text;
      nameNode = node.name;
    } else if (ts.isStringLiteral(node.name)) {
      name = node.name.text;
      nameNode = node.name;
    } else {
      return null;
    }

    const decorators = this.getDecoratorsOfDeclaration(node);
    const isStatic =
      node.modifiers !== undefined &&
      node.modifiers.some((mod) => mod.kind === ts.SyntaxKind.StaticKeyword);

    return {
      node,
      implementation: node,
      kind,
      type: node.type || null,
      name,
      nameNode,
      decorators,
      value,
      isStatic,
    };
  }
}

function parameterName(name: ts.BindingName): string | null {
  if (ts.isIdentifier(name)) {
    return name.text;
  } else {
    return null;
  }
}

/**
 * Compute the left most identifier in a qualified type chain. E.g. the `a` of `a.b.c.SomeType`.
 * @param qualifiedName The starting property access expression from which we want to compute
 * the left most identifier.
 * @returns the left most identifier in the chain or `null` if it is not an identifier.
 */
function getQualifiedNameRoot(
  qualifiedName: ts.QualifiedName
): ts.Identifier | null {
  while (ts.isQualifiedName(qualifiedName.left)) {
    qualifiedName = qualifiedName.left;
  }
  return ts.isIdentifier(qualifiedName.left) ? qualifiedName.left : null;
}

/**
 * Compute the left most identifier in a property access chain. E.g. the `a` of `a.b.c.d`.
 * @param propertyAccess The starting property access expression from which we want to compute
 * the left most identifier.
 * @returns the left most identifier in the chain or `null` if it is not an identifier.
 */
function getFarLeftIdentifier(
  propertyAccess: ts.PropertyAccessExpression
): ts.Identifier | null {
  while (ts.isPropertyAccessExpression(propertyAccess.expression)) {
    propertyAccess = propertyAccess.expression;
  }
  return ts.isIdentifier(propertyAccess.expression)
    ? propertyAccess.expression
    : null;
}

/**
 * Return the ImportDeclaration for the given `node` if it is either an `ImportSpecifier` or a
 * `NamespaceImport`. If not return `null`.
 */
function getContainingImportDeclaration(
  node: ts.Node
): ts.ImportDeclaration | null {
  return ts.isImportSpecifier(node)
    ? node.parent.parent.parent
    : ts.isNamespaceImport(node)
    ? node.parent.parent
    : null;
}

/**
 * Compute the name by which the `decl` was exported, not imported.
 * If no such declaration can be found (e.g. it is a namespace import)
 * then fallback to the `originalId`.
 */
function getExportedName(
  decl: ts.Declaration,
  originalId: ts.Identifier
): string {
  return ts.isImportSpecifier(decl)
    ? (decl.propertyName !== undefined ? decl.propertyName : decl.name).text
    : originalId.text;
}
