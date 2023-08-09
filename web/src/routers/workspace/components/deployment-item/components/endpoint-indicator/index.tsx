import { FC } from "react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Cloud, CloudOffline, CopyFile } from "@carbon/icons-react";
import { Popover, Typography } from "antd";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { combineLatestWith, switchMap } from "rxjs";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";

export const EndpointIndicator: FC<{ endpoint: string }> = ({ endpoint }) => {
  const theme = useAntdTheme();
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const endpoint$ = useObservableFromState(endpoint);
  const connected = useStateFromObservable(
    () =>
      endpoint$
        .pipe(combineLatestWith(refreshService.refresh$))
        .pipe(switchMap(([p]) => deploymentService.endpointConnection(p))),
    false
  );

  return (
    <Description.Item
      icon={<CarbonIcon icon={connected ? <Cloud /> : <CloudOffline />} />}
      description={
        <Popover
          placement="bottom"
          content={
            connected ? undefined : "Cannot automatically verify connection"
          }
        >
          <Typography.Text
            css={css`
              max-width: 360px !important;
              cursor: ${connected ? "txt" : "default"};
            `}
            type={connected ? undefined : "secondary"}
            ellipsis={{
              tooltip: connected ? endpoint : false,
            }}
            copyable={{
              tooltips: false,
              icon: (
                <span
                  css={css`
                    color: ${connected
                      ? theme.colorText
                      : theme.colorTextTertiary};
                  `}
                >
                  <CarbonIcon icon={<CopyFile />} />
                </span>
              ),
              text: endpoint,
            }}
          >
            {endpoint}
          </Typography.Text>
        </Popover>
      }
    />
  );
};
