import ts from "typescript";
import { TypeScriptReflectionHost } from "./reflection/typescript";
import { visit } from "./transformer/visitor";
import { TransformationVisitor } from "./transformer/transformation";
import { CompilationVisitor } from "./transformer/compilation";

const transformer: (
  program: ts.Program
) => ts.TransformerFactory<ts.SourceFile> =
  (program) => (context) => (sourceFile) => {
    const checker = program.getTypeChecker();
    const reflector = new TypeScriptReflectionHost(checker);
    // The transformation process consists of 2 steps:
    //
    //  1. Visit all classes, perform compilation and collect the results.
    //  2. Perform actual transformation of required TS nodes using compilation results from the first
    //     step.
    //
    // This is needed to have all `Expression`s generated before any TS transforms happen. This
    // allows `classCompilationMap` to properly identify expressions that can be shared across multiple
    // components declared in the same file.

    // Step 1. Go through all classes in AST, perform compilation and collect the results.
    const compilationVisitor = new CompilationVisitor(reflector);
    visit(sourceFile, compilationVisitor, context);
    // Step 2. Scan through the AST again and perform transformations based on compilation
    // results obtained at Step 1.
    const transformationVisitor = new TransformationVisitor(
      compilationVisitor.classCompilationMap,
      compilationVisitor.importsToPreserve
    );
    return visit(sourceFile, transformationVisitor, context);
  };

export default transformer;
