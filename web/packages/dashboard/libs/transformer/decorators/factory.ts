import { Identifiers } from "../util/identifiers";
import {
  importExpr,
  InstantiateExpr,
  literalArr,
  OutputExpression,
} from "./expression";
import { CtorParameter } from "../reflection/host";

export interface DependencyMetadata {
  /**
   * original constructor parameter of the dependency
   */
  param: CtorParameter;
  /**
   * An expression representing the token or value to be injected.
   * Or `null` if the dependency could not be resolved - making it invalid.
   */
  token: OutputExpression | null;

  /**
   * Whether the dependency has an @Optional qualifier.
   */
  optional: boolean;

  /**
   * Whether the dependency has an @Self qualifier.
   */
  self: boolean;

  /**
   * Whether the dependency has an @SkipSelf qualifier.
   */
  skipSelf: boolean;
}

export function compileInjectableFn(
  deps: DependencyMetadata[] | null
): OutputExpression | null {
  let ctorExpr: OutputExpression[] = [];
  if (deps !== null) {
    // There is a constructor (either explicitly or implicitly defined).
    ctorExpr = deps
      .filter((dep) => !!dep.token)
      .map((dep) => {
        const depsExpr = [
          new InstantiateExpr(importExpr(Identifiers.inject), [dep.token!]),
        ];
        if (dep.self) {
          depsExpr.unshift(
            new InstantiateExpr(importExpr(Identifiers.self), [])
          );
        }
        if (dep.skipSelf) {
          depsExpr.unshift(
            new InstantiateExpr(importExpr(Identifiers.skipSelf), [])
          );
        }
        if (dep.optional) {
          depsExpr.unshift(
            new InstantiateExpr(importExpr(Identifiers.optional), [])
          );
        }
        return literalArr(depsExpr);
      });
  }

  if (ctorExpr.length === 0) {
    return null;
  } else {
    return literalArr(ctorExpr);
  }
}
