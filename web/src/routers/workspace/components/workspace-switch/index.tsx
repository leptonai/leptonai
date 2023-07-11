import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { Select } from "antd";
import { FC } from "react";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

export const WorkspaceSwitch: FC = () => {
  const profileService = useInject(ProfileService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const navigateService = useInject(NavigateService);
  const theme = useAntdTheme();
  const options =
    profileService.profile?.authorized_workspaces?.map((c) => {
      return {
        label: c.data.cluster_name,
        value: c.data.cluster_name,
      };
    }) || [];

  const changeWorkspace = (workspace: string) => {
    if (workspace !== workspaceTrackerService.name) {
      navigateService.navigateTo("workspace", {
        workspaceId: workspace,
      });
    }
  };
  return (
    <div
      className="workspace-switch"
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
            popupMatchSelectWidth={false}
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
