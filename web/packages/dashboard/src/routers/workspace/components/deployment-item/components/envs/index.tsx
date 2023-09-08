import { css } from "@emotion/react";
import { FC } from "react";
import {
  Deployment,
  DeploymentEnv,
  DeploymentSecretEnv,
} from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Asterisk, Hashtag, ListDropdown } from "@carbon/icons-react";
import { Descriptions, Popover, Tag } from "antd";
import { LinkTo } from "@lepton-dashboard/components/link-to";

const DescriptionLabel: FC<{ data: DeploymentEnv | DeploymentSecretEnv }> = ({
  data,
}) => {
  const secretRef = (data as unknown as DeploymentSecretEnv)?.value_from
    ?.secret_name_ref;
  if (secretRef) {
    return (
      <LinkTo name="settingsSecrets">
        <Tag color="default" icon={<CarbonIcon icon={<Asterisk />} />}>
          {secretRef}
        </Tag>
      </LinkTo>
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
        <span
          css={css`
            &:hover {
              text-decoration: underline;
              cursor: pointer;
            }
          `}
        >
          <Description.Item
            icon={<CarbonIcon icon={<ListDropdown />} />}
            description="Environment variables"
          />
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
