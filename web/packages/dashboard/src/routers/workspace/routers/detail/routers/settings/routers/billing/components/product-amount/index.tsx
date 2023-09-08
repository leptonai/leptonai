import { Tag } from "antd";
import Decimal from "decimal.js";
import { FC, useMemo } from "react";

export const ProductAmount: FC<{ amount: number }> = ({ amount }) => {
  const amountString = new Decimal(amount).div(100).toFixed();
  const isNegative = amountString.indexOf("-") !== -1;
  const amountDisplay = useMemo(() => {
    if (isNegative) {
      return `-$${amountString.replace("-", "")}`;
    } else {
      return `$${amountString}`;
    }
  }, [amountString, isNegative]);
  return <Tag bordered={false}>{amountDisplay}</Tag>;
};
