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
  } & EmotionProps
> = ({ date, detail, prefix, suffix, className }) => {
  const format = dayjs(date).isSame(new Date(), "year")
    ? "MMM D, h:mm A"
    : "MMM D, YYYY";

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
                title: `${dayjs.tz.guess()} · Computer`,
                label: dayjs(date).format(detailedFormat),
              },
            ]}
          />
        }
        placement="bottom"
      >
        <span>
          <Link className={className}>
            {prefix} {dayjs(date).format(detail ? detailedFormat : format)}{" "}
            {suffix}
          </Link>
        </span>
      </Popover>
    </MinThemeProvider>
  );
};
