import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { Select } from "antd";
import { FC } from "react";
import { useNavigate } from "react-router-dom";

export const WorkspaceSwitch: FC = () => {
  const profileSevice = useInject(ProfileService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const navigate = useNavigate();
  const theme = useAntdTheme();
  const options =
    profileSevice.profile?.authorized_clusters?.map((c) => {
      return {
        label: c.data.cluster_name,
        value: c.data.cluster_name,
      };
    }) || [];

  const changeWorkspace = (workspace: string) => {
    if (workspace !== workspaceTrackerService.name) {
      navigate(`/workspace/${workspace}`);
    }
  };
  return (
    <div
      css={css`
        display: flex;
        align-items: center;
      `}
    >
      <div
        css={css`
          font-size: 24px;
          margin-left: 12px;
          font-weight: 300;
          position: relative;
          top: -1px;
          color: ${theme.colorTextDescription};
        `}
      >
        /
      </div>

      <div>
        {options.length > 1 ? (
          <Select
            size="large"
            dropdownMatchSelectWidth={false}
            bordered={false}
            showArrow={false}
            onChange={(v) => changeWorkspace(v)}
            value={workspaceTrackerService.name}
            options={options}
          />
        ) : (
          <div
            css={css`
              font-size: 16px;
              padding: 0 11px;
              cursor: default;
              color: ${theme.colorText};
            `}
          >
            {workspaceTrackerService.name}
          </div>
        )}
      </div>
    </div>
  );
};
