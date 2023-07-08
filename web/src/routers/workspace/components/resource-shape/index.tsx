import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { HardwareService } from "@lepton-dashboard/services/hardware.service";
import { useInject } from "@lepton-libs/di";
import { Tag } from "antd";
import { FC } from "react";

export const ResourceShape: FC<{ shape: string }> = ({ shape }) => {
  const hardwareService = useInject(HardwareService);
  const resourceShape = hardwareService.hardwareShapes[shape];
  const theme = useAntdTheme();
  return resourceShape ? (
    <div>
      <div
        css={css`
          font-size: 14px;
          font-weight: 500;
          color: ${theme.colorTextHeading};
        `}
      >
        {resourceShape.DisplayName}
        {resourceShape.Resource.AcceleratorType && (
          <Tag
            color="lime"
            css={css`
              line-height: 16px;
              margin-left: 6px;
            `}
          >
            {resourceShape.Resource.AcceleratorType} ×{" "}
            {`${resourceShape.Resource.AcceleratorNum}`}
          </Tag>
        )}
      </div>
      <div
        css={css`
          margin-top: 2px;
          font-size: 12px !important;
          font-weight: 400;
          color: ${theme.colorTextSecondary};
        `}
      >
        CPU: {resourceShape.Resource.CPU}, Memory:{" "}
        {resourceShape.Resource.Memory / 1024} GB, Storage:{" "}
        {resourceShape.Resource.EphemeralStorageInGB} GB
      </div>
    </div>
  ) : (
    <>{shape}</>
  );
};
