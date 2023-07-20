import { css } from "@emotion/react";
import Decimal from "decimal.js";
import { FC } from "react";

export const PriceSummary: FC<{
  name: string;
  amount: number;
  prefix?: string;
}> = ({ name, amount, prefix }) => {
  return (
    <div
      css={css`
        justify-content: end;
        display: flex;
      `}
    >
      <span
        css={css`
          font-weight: bold;
          margin-right: 24px;
          flex: 0 0 100px;
        `}
      >
        {name}
      </span>
      <span
        css={css`
          font-weight: bold;
          flex: 0 0 150px;
        `}
      >
        {prefix} ${new Decimal(amount).dividedBy(100).toFixed()}
      </span>
    </div>
  );
};
