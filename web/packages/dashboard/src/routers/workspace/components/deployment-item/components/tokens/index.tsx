import { Password } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import {
  DeploymentToken,
  Token,
} from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { Descriptions, Input, Popover } from "antd";
import { FC } from "react";

export const Tokens: FC<{ tokens?: Token[] }> = ({ tokens }) => {
  const deploymentTokens = (tokens || []).filter(
    (t): t is DeploymentToken => "value" in t
  );
  if (deploymentTokens && deploymentTokens.length > 0) {
    return (
      <Popover
        placement="bottomLeft"
        content={
          <Descriptions column={1} size="small" bordered>
            {deploymentTokens.map((token) => {
              return (
                <Descriptions.Item key={token.value}>
                  <Input.Password
                    size="small"
                    value={token.value}
                    bordered={false}
                    readOnly
                  />
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
            icon={<CarbonIcon icon={<Password />} />}
            description="Deployment tokens"
          />
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
