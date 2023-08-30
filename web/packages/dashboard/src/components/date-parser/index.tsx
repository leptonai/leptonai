import { Link } from "@lepton-dashboard/components/link";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { Popover, Table } from "antd";
import { FC } from "react";
import dayjs, { ConfigType } from "dayjs";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const DateParser: FC<
  {
    date: ConfigType;
    detail?: boolean;
    prefix?: string;
    suffix?: string;
    format?: string;
  } & EmotionProps
> = ({ date, detail, prefix, format, suffix, className }) => {
  const defaultFormat =
    format ||
    (dayjs(date).isSame(new Date(), "year") ? "MMM D, h:mm A" : "MMM D, YYYY");

  const detailedFormat = "h:mm A, MMM D, YYYY";

  return (
    <MinThemeProvider>
      <Popover
        title="Time conversion"
        content={
          <Table
            size="small"
            showHeader={false}
            pagination={false}
            rowKey="title"
            columns={[{ dataIndex: "title" }, { dataIndex: "label" }]}
            dataSource={[
              {
                title: "UTC",
                label: dayjs(date).utc().format(detailedFormat),
              },
              {
                title: `${dayjs.tz.guess()}`,
                label: dayjs(date).format(detailedFormat),
              },
            ]}
          />
        }
        placement="bottom"
      >
        <span>
          <Link className={className}>
            {prefix}{" "}
            {dayjs(date).format(detail ? detailedFormat : defaultFormat)}{" "}
            {suffix}
          </Link>
        </span>
      </Popover>
    </MinThemeProvider>
  );
};
