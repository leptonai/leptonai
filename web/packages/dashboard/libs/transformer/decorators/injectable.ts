import { NamedClassDeclaration } from "../reflection/host";
import { compileInjectableFn, DependencyMetadata } from "./factory";
import { FatalDiagnosticError } from "./error";
import { TypeScriptReflectionHost } from "../reflection/typescript";
import { Identifiers } from "../util/identifiers";
import { OutputExpression } from "./expression";

/**
 * Generate a description of the field which should be added to the class, including any
 * initialization code to be generated.
 *
 * If the compilation mode is configured as partial, and an implementation of `compilePartial` is
 * provided, then this method is not called.
 */
export function compile(
  node: NamedClassDeclaration,
  deps: DependencyMetadata[] | null,
  reflector: TypeScriptReflectionHost
): OutputExpression[] {
  const results: OutputExpression[] = [];
  const staticParams = reflector
    .getMembersOfClass(node)
    .find((member) => member.name === Identifiers.parameters);
  if (staticParams !== undefined) {
    throw new FatalDiagnosticError(
      staticParams.nameNode || staticParams.node || node,
      "Injectables cannot contain a static parameters property, because the compiler is going to generate one."
    );
  } else {
    // Only add a new parameters if there is not one already
    const expression = compileInjectableFn(deps);
    if (expression) {
      results.push(expression);
    }
  }

  return results;
}
