import ts from "typescript";

import {
  NamedClassDeclaration,
  CtorParameter,
  TypeValueReferenceKind,
  UnavailableValue,
  ValueUnavailableKind,
} from "../reflection/host";

import { isTargetDecorator, valueReferenceToExpression } from "../util/util";
import { DependencyMetadata } from "./factory";
import { WrappedNodeExpr } from "./expression";
import { FatalDiagnosticError, makeRelatedInformation } from "./error";
import { TypeScriptReflectionHost } from "../reflection/typescript";
import { Identifiers } from "../util/identifiers";

export type ConstructorDeps =
  | {
      deps: DependencyMetadata[];
    }
  | {
      deps: null;
      errors: ConstructorDepError[];
    };

export interface ConstructorDepError {
  index: number;
  param: CtorParameter;
  reason: UnavailableValue;
}

/**
 * Creates a fatal error with diagnostic for an invalid injection token.
 * @param clazz The class for which the injection token was unavailable.
 * @param error The reason why no valid injection token is available.
 */
function createUnsuitableInjectionTokenError(
  clazz: NamedClassDeclaration,
  error: ConstructorDepError
): FatalDiagnosticError {
  const { param, index, reason } = error;
  let chainMessage: string | undefined;
  let hints: ts.DiagnosticRelatedInformation[] | undefined;
  switch (reason.kind) {
    case ValueUnavailableKind.UNSUPPORTED:
      chainMessage =
        "Consider using the @Inject decorator to specify an injection token.";
      hints = [
        makeRelatedInformation(
          reason.typeNode,
          "This type is not supported as injection token."
        ),
      ];
      break;
    case ValueUnavailableKind.NO_VALUE_DECLARATION:
      chainMessage =
        "Consider using the @Inject decorator to specify an injection token.";
      hints = [
        makeRelatedInformation(
          reason.typeNode,
          "This type does not have a value, so it cannot be used as injection token."
        ),
      ];
      if (reason.decl !== null) {
        hints.push(
          makeRelatedInformation(reason.decl, "The type is declared here.")
        );
      }
      break;
    case ValueUnavailableKind.TYPE_ONLY_IMPORT:
      chainMessage =
        "Consider changing the type-only import to a regular import, or use the @Inject decorator to specify an injection token.";
      hints = [
        makeRelatedInformation(
          reason.typeNode,
          "This type is imported using a type-only import, which prevents it from being usable as an injection token."
        ),
        makeRelatedInformation(
          reason.node,
          "The type-only import occurs here."
        ),
      ];
      break;
    case ValueUnavailableKind.NAMESPACE:
      chainMessage =
        "Consider using the @Inject decorator to specify an injection token.";
      hints = [
        makeRelatedInformation(
          reason.typeNode,
          "This type corresponds with a namespace, which cannot be used as injection token."
        ),
        makeRelatedInformation(
          reason.importClause,
          "The namespace import occurs here."
        ),
      ];
      break;
    case ValueUnavailableKind.UNKNOWN_REFERENCE:
      chainMessage = "The type should reference a known declaration.";
      hints = [
        makeRelatedInformation(
          reason.typeNode,
          "This type could not be resolved."
        ),
      ];
      break;
    case ValueUnavailableKind.MISSING_TYPE:
      chainMessage =
        "Consider adding a type to the parameter or use the @Inject decorator to specify an injection token.";
      break;
    default:
      break;
  }

  const chain: ts.DiagnosticMessageChain = {
    messageText: `No suitable injection token for parameter '${
      param.name || index
    }' of class '${clazz.name.text}'.`,
    category: ts.DiagnosticCategory.Error,
    code: 0,
    next: [
      {
        messageText: chainMessage!,
        category: ts.DiagnosticCategory.Message,
        code: 0,
      },
    ],
  };

  return new FatalDiagnosticError(param.nameNode, chain, hints);
}

/**
 * Validate that `ConstructorDeps` does not have any invalid dependencies and convert them into the
 * `DependencyMetadata` array if so, or raise a diagnostic if some deps are invalid.
 *
 * This is a companion function to `unwrapConstructorDependencies` which does not accept invalid
 * deps.
 */
export function validateConstructorDependencies(
  clazz: NamedClassDeclaration,
  deps: ConstructorDeps | null
): DependencyMetadata[] | null {
  if (deps === null) {
    return null;
  } else if (deps.deps !== null) {
    return deps.deps;
  } else {
    const error = deps.errors[0];
    throw createUnsuitableInjectionTokenError(clazz, error);
  }
}

function getConstructorDependencies(
  clazz: NamedClassDeclaration,
  reflector: TypeScriptReflectionHost
): ConstructorDeps | null {
  const deps: DependencyMetadata[] = [];
  const errors: ConstructorDepError[] = [];
  let ctorParams = reflector.getConstructorParameters(clazz);
  if (ctorParams === null) {
    if (reflector.hasBaseClass(clazz)) {
      return null;
    } else {
      ctorParams = [];
    }
  }

  ctorParams.forEach((param, idx) => {
    let token = valueReferenceToExpression(param.typeValueReference);
    let optional = false;
    let self = false;
    let skipSelf = false;

    (param.decorators || [])
      .filter((dec) => isTargetDecorator(dec))
      .forEach((dec) => {
        const name = dec.import === null ? dec.name : dec.import.name;
        if (name === Identifiers.inject) {
          token = new WrappedNodeExpr(dec.args![0]);
        } else if (name === Identifiers.optional) {
          optional = true;
        } else if (name === Identifiers.skipSelf) {
          skipSelf = true;
        } else if (name === Identifiers.self) {
          self = true;
        } else {
          throw new FatalDiagnosticError(
            dec.node,
            `Unexpected decorator ${name} on parameter.`
          );
        }
      });
    if (token === null) {
      if (
        param.typeValueReference.kind !== TypeValueReferenceKind.UNAVAILABLE
      ) {
        throw new Error(
          "Illegal state: expected value reference to be unavailable if no token is present"
        );
      }
      errors.push({
        index: idx,
        param,
        reason: param.typeValueReference.reason,
      });
    } else {
      deps.push({ param, token, optional, self, skipSelf });
    }
  });
  if (errors.length === 0) {
    return { deps };
  } else {
    return { deps: null, errors };
  }
}

export function extractInjectableCtorDeps(
  clazz: NamedClassDeclaration,
  reflector: TypeScriptReflectionHost
): DependencyMetadata[] | null {
  return validateConstructorDependencies(
    clazz,
    getConstructorDependencies(clazz, reflector)
  );
}
