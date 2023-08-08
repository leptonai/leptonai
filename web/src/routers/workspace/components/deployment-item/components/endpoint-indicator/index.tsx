import { FC } from "react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Api, CopyFile } from "@carbon/icons-react";
import { Badge, Tooltip, Typography } from "antd";
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
  const healthy = useStateFromObservable(
    () =>
      endpoint$
        .pipe(combineLatestWith(refreshService.refresh$))
        .pipe(switchMap(([p]) => deploymentService.endpointHealth(p))),
    false
  );

  return (
    <Description.Item
      icon={<CarbonIcon icon={<Api />} />}
      term="Endpoint"
      description={
        <Tooltip title={healthy ? undefined : "No connection to the endpoint"}>
          <Typography.Text
            type={healthy ? undefined : "secondary"}
            style={{ maxWidth: "280px" }}
            ellipsis={{
              tooltip: healthy ? endpoint : false,
            }}
            copyable={{
              tooltips: false,
              icon: (
                <span
                  css={css`
                    color: ${healthy
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
            <Badge status={healthy ? "success" : "default"} /> {endpoint}
          </Typography.Text>
        </Tooltip>
      }
    />
  );
};
