import ts from "typescript";
import { OutputExpression } from "../decorators/expression";

export interface CompilationResult {
  expressions: OutputExpression[];
}

export type ImportDeclarationSet = Set<ts.ImportDeclaration>;

export type ClassCompilationMap = Map<ts.ClassDeclaration, CompilationResult>;
