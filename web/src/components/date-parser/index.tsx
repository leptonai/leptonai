import { FC } from "react";
import dayjs, { ConfigType } from "dayjs";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props.ts";

export const DateParser: FC<
  {
    date: ConfigType;
    detail?: boolean;
    prefix?: string;
    suffix?: string;
  } & EmotionProps
> = ({ date, detail, prefix, suffix, className }) => {
  const format = dayjs(date).isSame(new Date(), "year")
    ? "MMMM D"
    : "MMMM D, YYYY";

  return (
    <span className={className} title={dayjs(date).format("L LT")}>
      {prefix} {dayjs(date).format(detail ? "LLL" : format)} {suffix}
    </span>
  );
};
