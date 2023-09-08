import { css } from "@emotion/react";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Alert } from "antd";
import { FC } from "react";

export const PastDueBanner: FC = () => {
  const theme = useAntdTheme();

  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const isPastDue = workspaceTrackerService.workspace?.isPastDue;
  if (isPastDue) {
    return (
      <Alert
        css={css`
          padding: 8px 40px;
          border-bottom: 1px solid ${theme.colorWarningBorder} !important;
        `}
        type="warning"
        banner
        message={
          <LinkTo
            css={css`
              white-space: break-spaces;
            `}
            name="settingsBilling"
            relative="route"
          >
            Your current workspace has an outstanding balance. Please proceed to
            the billing page to enter your payment info.
          </LinkTo>
        }
      />
    );
  } else {
    return <></>;
  }
};
