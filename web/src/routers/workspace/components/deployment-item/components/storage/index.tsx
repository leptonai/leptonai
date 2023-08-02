import { Link } from "@lepton-dashboard/components/link";
import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Folder } from "@carbon/icons-react";
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
          <Link>
            <Description.Item
              icon={<CarbonIcon icon={<Folder />} />}
              description="Storage mounts"
            />
          </Link>
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
