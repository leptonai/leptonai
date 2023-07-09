import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Folder } from "@carbon/icons-react";
import { Hoverable } from "@lepton-dashboard/routers/workspace/components/hoverable";
import { Descriptions, Popover, Tag } from "antd";

export const Storage: FC<{ mounts: Deployment["mounts"] }> = ({ mounts }) => {
  if (mounts && mounts.length > 0) {
    return (
      <Popover
        placement="bottomLeft"
        content={
          <Descriptions column={1} size="small" bordered>
            {mounts.map((mount) => {
              return (
                <Descriptions.Item
                  key={mount.path}
                  label={
                    <Tag icon={<CarbonIcon icon={<Folder />} />}>
                      {mount.path}
                    </Tag>
                  }
                >
                  {mount.mount_path}
                </Descriptions.Item>
              );
            })}
          </Descriptions>
        }
      >
        <span>
          <Hoverable>
            <Description.Item
              icon={<CarbonIcon icon={<Folder />} />}
              description="Storage mounts"
            />
          </Hoverable>
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
