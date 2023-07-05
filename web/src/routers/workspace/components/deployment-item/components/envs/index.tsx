import { css } from "@emotion/react";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { FC } from "react";
import {
  Deployment,
  DeploymentEnv,
  DeploymentSecretEnv,
} from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Asterisk, Hashtag, ListDropdown } from "@carbon/icons-react";
import { Hoverable } from "@lepton-dashboard/routers/workspace/components/hoverable";
import { Descriptions, Popover, Tag } from "antd";

const DescriptionLabel: FC<{ data: DeploymentEnv | DeploymentSecretEnv }> = ({
  data,
}) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const secretRef = (data as unknown as DeploymentSecretEnv)?.value_from
    ?.secret_name_ref;
  if (secretRef) {
    return (
      <Link to={`/workspace/${workspaceTrackerService.name}/settings/secrets`}>
        <Tag color="default" icon={<CarbonIcon icon={<Asterisk />} />}>
          {secretRef}
        </Tag>
      </Link>
    );
  } else {
    return (
      <Tag
        color="default"
        css={css`
          cursor: default;
        `}
        icon={<CarbonIcon icon={<Hashtag />} />}
      >
        {(data as unknown as DeploymentEnv)?.value}
      </Tag>
    );
  }
};

export const Envs: FC<{ envs: Deployment["envs"] }> = ({ envs }) => {
  if (envs && envs.length > 0) {
    return (
      <Popover
        placement="bottomLeft"
        content={
          <Descriptions column={1} size="small" bordered>
            {envs.map((env) => {
              return (
                <Descriptions.Item key={env.name} label={env.name}>
                  <DescriptionLabel data={env} />
                </Descriptions.Item>
              );
            })}
          </Descriptions>
        }
      >
        <span>
          <Hoverable>
            <Description.Item
              icon={<CarbonIcon icon={<ListDropdown />} />}
              description="Secret & Variables"
            />
          </Hoverable>
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
