import ts from "typescript";

/**
 * Metadata extracted from an instance of a decorator on another declaration, which was actually
 * present in a file.
 *
 * Concrete decorators always have an `identifier` and a `node`.
 */
export interface Decorator {
  /**
   * Name by which the decorator was invoked in the user's code.
   *
   * This is distinct from the name by which the decorator was imported (though in practice they
   * will usually be the same).
   */
  name: string;

  /**
   * `Import` by which the decorator was brought into the module in which it was invoked, or `null`
   * if the decorator was declared in the same module and not imported.
   */
  import: Import | null;

  /**
   * TypeScript references to the decorator itself
   */
  node: ts.Decorator;

  /**
   * Arguments of the invocation of the decorator, if the decorator is invoked, or `null`
   * otherwise.
   */
  args: ts.Expression[] | null;
}

/**
 * A decorator is identified by either a simple identifier (e.g. `Decorator`) or, in some cases,
 * a namespaced property access (e.g. `core.Decorator`).
 */
export type DecoratorIdentifier = ts.Identifier | NamespacedIdentifier;
export type NamespacedIdentifier = ts.PropertyAccessExpression & {
  expression: ts.Identifier;
  name: ts.Identifier;
};
export function isDecoratorIdentifier(
  exp: ts.Expression
): exp is DecoratorIdentifier {
  return (
    ts.isIdentifier(exp) ||
    (ts.isPropertyAccessExpression(exp) &&
      ts.isIdentifier(exp.expression) &&
      ts.isIdentifier(exp.name))
  );
}

/**
 * The `ts.Declaration` of a "class".
 *
 * Classes are represented differently in different code formats:
 * - In TS code, they are typically defined using the `class` keyword.
 * - In ES2015 code, they are usually defined using the `class` keyword, but they can also be
 *   variable declarations, which are initialized to a class expression (e.g.
 *   `let Foo = Foo1 = class Foo {}`).
 * - In ES5 code, they are typically defined as variable declarations being assigned the return
 *   value of an IIFE. The actual "class" is implemented as a constructor function inside the IIFE,
 *   but the outer variable declaration represents the "class" to the rest of the program.
 *
 * For `ReflectionHost` purposes, a class declaration should always have a `name` identifier,
 * because we need to be able to reference it in other parts of the program.
 */
export type NamedClassDeclaration = ts.ClassDeclaration & {
  name: ts.Identifier;
};

/**
 * An enumeration of possible kinds of class members.
 */
export enum ClassMemberKind {
  Constructor,
  Getter,
  Setter,
  Property,
  Method,
}

/**
 * A member of a class, such as a property, method, or constructor.
 */
export interface ClassMember {
  /**
   * TypeScript reference to the class member itself, or null if it is not applicable.
   */
  node: ts.Node | null;

  /**
   * Indication of which type of member this is (property, method, etc).
   */
  kind: ClassMemberKind;

  /**
   * TypeScript `ts.TypeNode` representing the type of the member, or `null` if not present or
   * applicable.
   */
  type: ts.TypeNode | null;

  /**
   * Name of the class member.
   */
  name: string;

  /**
   * TypeScript `ts.Identifier` or `ts.StringLiteral` representing the name of the member, or `null`
   * if no such node is present.
   *
   * The `nameNode` is useful in writing references to this member that will be correctly source-
   * mapped back to the original file.
   */
  nameNode: ts.Identifier | ts.StringLiteral | null;

  /**
   * TypeScript `ts.Expression` which represents the value of the member.
   *
   * If the member is a property, this will be the property initializer if there is one, or null
   * otherwise.
   */
  value: ts.Expression | null;

  /**
   * TypeScript `ts.Declaration` which represents the implementation of the member.
   *
   * In TypeScript code this is identical to the node, but in downleveled code this should always be
   * the Declaration which actually represents the member's runtime value.
   *
   * For example, the TS code:
   *
   * ```
   * class Clazz {
   *   static get property(): string {
   *     return 'value';
   *   }
   * }
   * ```
   *
   * Downlevels to:
   *
   * ```
   * var Clazz = (function () {
   *   function Clazz() {
   *   }
   *   Object.defineProperty(Clazz, "property", {
   *       get: function () {
   *           return 'value';
   *       },
   *       enumerable: true,
   *       configurable: true
   *   });
   *   return Clazz;
   * }());
   * ```
   *
   * In this example, for the property "property", the node would be the entire
   * Object.defineProperty ExpressionStatement, but the implementation would be this
   * FunctionDeclaration:
   *
   * ```
   * function () {
   *   return 'value';
   * },
   * ```
   */
  implementation: ts.Declaration | null;

  /**
   * Whether the member is static or not.
   */
  isStatic: boolean;

  /**
   * Any `Decorator`s which are present on the member, or `null` if none are present.
   */
  decorators: Decorator[] | null;
}

export const enum TypeValueReferenceKind {
  LOCAL,
  IMPORTED,
  UNAVAILABLE,
}

/**
 * A type reference that refers to any type via a `ts.Expression` that's valid within the local file
 * where the type was referenced.
 */
export interface LocalTypeValueReference {
  kind: TypeValueReferenceKind.LOCAL;

  /**
   * The synthesized expression to reference the type in a value position.
   */
  expression: ts.Expression;
}

/**
 * A reference that refers to a type that was imported, and gives the symbol `name` and the
 * `moduleName` of the import. Note that this `moduleName` may be a relative path, and thus is
 * likely only valid within the context of the file which contained the original type reference.
 */
export interface ImportedTypeValueReference {
  kind: TypeValueReferenceKind.IMPORTED;

  /**
   * The module specifier from which the `importedName` symbol should be imported.
   */
  moduleName: string;

  /**
   * The name of the top-level symbol that is imported from `moduleName`. If `nestedPath` is also
   * present, a nested object is being referenced from the top-level symbol.
   */
  importedName: string;

  /**
   * If present, represents the symbol names that are referenced from the top-level import.
   * When `null` or empty, the `importedName` itself is the symbol being referenced.
   */
  nestedPath: string[] | null;
  importSpecifier: ts.ImportSpecifier | null;
}

/**
 * A representation for a type value reference that is used when no value is available. This can
 * occur due to various reasons, which is indicated in the `reason` field.
 */
export interface UnavailableTypeValueReference {
  kind: TypeValueReferenceKind.UNAVAILABLE;

  /**
   * The reason why no value reference could be determined for a type.
   */
  reason: UnavailableValue;
}

/**
 * The various reasons why the compiler may be unable to synthesize a value from a type reference.
 */
export const enum ValueUnavailableKind {
  /**
   * No type node was available.
   */
  MISSING_TYPE,

  /**
   * The type does not have a value declaration, e.g. an interface.
   */
  NO_VALUE_DECLARATION,

  /**
   * The type is imported using a type-only imports, so it is not suitable to be used in a
   * value-position.
   */
  TYPE_ONLY_IMPORT,

  /**
   * The type reference could not be resolved to a declaration.
   */
  UNKNOWN_REFERENCE,

  /**
   * The type corresponds with a namespace.
   */
  NAMESPACE,

  /**
   * The type is not supported in the compiler, for example union types.
   */
  UNSUPPORTED,
}

export interface UnsupportedType {
  kind: ValueUnavailableKind.UNSUPPORTED;
  typeNode: ts.TypeNode;
}

export interface NoValueDeclaration {
  kind: ValueUnavailableKind.NO_VALUE_DECLARATION;
  typeNode: ts.TypeNode;
  decl: ts.Declaration | null;
}

export interface TypeOnlyImport {
  kind: ValueUnavailableKind.TYPE_ONLY_IMPORT;
  typeNode: ts.TypeNode;
  node: ts.ImportClause | ts.ImportSpecifier;
}

export interface NamespaceImport {
  kind: ValueUnavailableKind.NAMESPACE;
  typeNode: ts.TypeNode;
  importClause: ts.ImportClause;
}

export interface UnknownReference {
  kind: ValueUnavailableKind.UNKNOWN_REFERENCE;
  typeNode: ts.TypeNode;
}

export interface MissingType {
  kind: ValueUnavailableKind.MISSING_TYPE;
}

/**
 * The various reasons why a type node may not be referred to as a value.
 */
export type UnavailableValue =
  | UnsupportedType
  | NoValueDeclaration
  | TypeOnlyImport
  | NamespaceImport
  | UnknownReference
  | MissingType;

/**
 * A reference to a value that originated from a type position.
 *
 * For example, a constructor parameter could be declared as `foo: Foo`. A `TypeValueReference`
 * extracted from this would refer to the value of the class `Foo` (assuming it was actually a
 * type).
 *
 * See the individual types for additional information.
 */
export type TypeValueReference =
  | LocalTypeValueReference
  | ImportedTypeValueReference
  | UnavailableTypeValueReference;

/**
 * A parameter to a constructor.
 */
export interface CtorParameter {
  /**
   * Name of the parameter, if available.
   *
   * Some parameters don't have a simple string name (for example, parameters which are destructured
   * into multiple variables). In these cases, `name` can be `null`.
   */
  name: string | null;

  /**
   * TypeScript `ts.BindingName` representing the name of the parameter.
   *
   * The `nameNode` is useful in writing references to this member that will be correctly source-
   * mapped back to the original file.
   */
  nameNode: ts.BindingName;

  /**
   * Reference to the value of the parameter's type annotation, if it's possible to refer to the
   * parameter's type as a value.
   *
   * This can either be a reference to a local value, a reference to an imported value, or no
   * value if no is present or cannot be represented as an expression.
   */
  typeValueReference: TypeValueReference;

  /**
   * TypeScript `ts.TypeNode` representing the type node found in the type position.
   *
   * This field can be used for diagnostics reporting if `typeValueReference` is `null`.
   *
   * Can be null, if the param has no type declared.
   */
  typeNode: ts.TypeNode | null;

  /**
   * Any `Decorator`s which are present on the parameter, or `null` if none are present.
   */
  decorators: Decorator[] | null;
}

/**
 * The source of an imported symbol, including the original symbol name and the module from which it
 * was imported.
 */
export interface Import {
  /**
   * The name of the imported symbol under which it was exported (not imported).
   */
  name: string;

  /**
   * The module from which the symbol was imported.
   */
  from: string;
}
