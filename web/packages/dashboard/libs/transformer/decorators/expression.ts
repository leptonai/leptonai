import ts from "typescript";

export abstract class OutputExpression {
  abstract createExpression(): ts.Expression;
}

export class WrappedNodeExpr extends OutputExpression {
  constructor(public node: ts.Expression) {
    super();
  }

  override createExpression(): ts.Expression {
    return this.node;
  }
}

export class InstantiateExpr extends OutputExpression {
  constructor(
    public classExpr: OutputExpression,
    public args: OutputExpression[]
  ) {
    super();
  }

  override createExpression(): ts.NewExpression {
    return ts.factory.createNewExpression(
      this.classExpr.createExpression(),
      undefined,
      this.args.map((arg) => arg.createExpression())
    );
  }
}

export class ExternalExpr extends OutputExpression {
  constructor(public name: string) {
    super();
  }

  override createExpression(): ts.Identifier {
    if (this.name === null) {
      throw new Error("Invalid import without name nor moduleName");
    }
    return ts.factory.createIdentifier(this.name);
  }
}

export class ReadPropExpr extends OutputExpression {
  constructor(public receiver: OutputExpression, public name: string) {
    super();
  }

  override createExpression(): ts.PropertyAccessExpression {
    return ts.factory.createPropertyAccessExpression(
      this.receiver.createExpression(),
      this.name
    );
  }
}

export class LiteralArrayExpr extends OutputExpression {
  public entries: OutputExpression[];

  constructor(entries: OutputExpression[]) {
    super();
    this.entries = entries;
  }

  override createExpression(): ts.ArrayLiteralExpression {
    return ts.factory.createArrayLiteralExpression(
      this.entries.map((expr) => expr.createExpression())
    );
  }
}

export function importExpr(name: string): ExternalExpr {
  return new ExternalExpr(name);
}

export function literalArr(values: OutputExpression[]): LiteralArrayExpr {
  return new LiteralArrayExpr(values);
}
