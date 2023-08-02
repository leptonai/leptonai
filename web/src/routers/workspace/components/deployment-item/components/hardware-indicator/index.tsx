import { Chip } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/components/link";
import { ResourceShape } from "@lepton-dashboard/routers/workspace/components/resource-shape";
import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { useInject } from "@lepton-libs/di";
import { Popover, Tag } from "antd";
import { FC } from "react";

export const HardwareIndicator: FC<{ shape?: string }> = ({ shape }) => {
  const hardwareService = useInject(HardwareService);
  return shape && hardwareService.hardwareShapes[shape] ? (
    <Popover
      placement="bottomLeft"
      content={
        <div
          css={css`
            cursor: default;
          `}
        >
          <ResourceShape shape={shape} />
        </div>
      }
    >
      <span
        css={css`
          cursor: default;
        `}
      >
        <Tag bordered={false} icon={<CarbonIcon icon={<Chip />} />}>
          <Link>{hardwareService.hardwareShapes[shape].DisplayName}</Link>
        </Tag>
      </span>
    </Popover>
  ) : null;
};
