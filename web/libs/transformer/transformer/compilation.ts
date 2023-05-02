import ts from "typescript";
import { Visitor } from "./visitor";
import { TypeScriptReflectionHost } from "../reflection/typescript";
import { findTargetDecorator, isNamedClassDeclaration } from "../util/util";
import { extractInjectableCtorDeps } from "../decorators/di";
import { compile } from "../decorators/injectable";
import { Identifiers } from "../util/identifiers";
import { ClassCompilationMap, ImportDeclarationSet } from "./type";
import {
  ImportedTypeValueReference,
  TypeValueReferenceKind,
} from "../reflection/host";

/**
 * Visits all classes, performs compilation where target decorators are present and collects
 * result in a Map that associates a ts.ClassDeclaration with compilation results. This visitor
 * does NOT perform any TS transformations.
 *
 */
export class CompilationVisitor extends Visitor {
  public classCompilationMap: ClassCompilationMap = new Map();

  public importsToPreserve: ImportDeclarationSet = new Set();

  constructor(private reflector: TypeScriptReflectionHost) {
    super();
  }

  override visitClassDeclaration(
    node: ts.ClassDeclaration
  ): ts.ClassDeclaration {
    const original = ts.getOriginalNode(node);
    if (isNamedClassDeclaration(node) && isNamedClassDeclaration(original)) {
      const decorators = this.reflector.getDecoratorsOfDeclaration(node);
      const decorator = findTargetDecorator(
        decorators || [],
        Identifiers.injectable
      );
      if (decorator) {
        const deps = extractInjectableCtorDeps(node, this.reflector);
        const importSpecifiers = (deps || [])
          .map((dep) => dep.param.typeValueReference)
          .filter(
            (ref): ref is ImportedTypeValueReference =>
              ref.kind === TypeValueReferenceKind.IMPORTED &&
              !!ref.importSpecifier
          )
          .map((ref) => ref.importSpecifier!);
        importSpecifiers.forEach((spec) => {
          const importDecl = spec.parent.parent.parent;
          this.importsToPreserve.add(importDecl);
        });
        const expressions = compile(node, deps, this.reflector);
        this.classCompilationMap.set(node, { expressions });
      }
    }
    return node;
  }
}
