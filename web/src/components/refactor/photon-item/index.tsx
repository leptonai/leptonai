import { FC } from "react";
import { PhotonGroup } from "@lepton-dashboard/interfaces/photon.ts";
import { Description } from "../description";
import { DataParser } from "@lepton-dashboard/components/refactor/data-parser";
import { Button, Col, Row, Tag } from "antd";
import { Link } from "@lepton-dashboard/components/link";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Time, Version } from "@carbon/icons-react";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { useNavigate } from "react-router-dom";
import { PopoverDeploymentTable } from "@lepton-dashboard/components/refactor/popover-deployment-table";

export const PhotonItem: FC<{ photon?: PhotonGroup }> = ({ photon }) => {
  const theme = useAntdTheme();
  const navigate = useNavigate();
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const relatedDeployments = deployments.filter((d) =>
    (photon?.versions || []).some((v) => v.id === d.photon_id)
  );
  return photon ? (
    <Row>
      <Col span={24}>
        <Row>
          <Col flex="1 1 auto">
            <Link
              css={css`
                color: ${theme.colorTextHeading};
              `}
              to={`/photons/versions/${photon.name}`}
              relative="route"
            >
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                icon={<PhotonIcon />}
                term={photon.name}
              />
            </Link>
          </Col>
          <Col flex="0 0 auto">
            <Button
              size="small"
              icon={<DeploymentIcon />}
              onClick={() =>
                navigate(`/deployments/create/${photon.id}`, {
                  relative: "route",
                })
              }
            >
              Deploy
            </Button>
          </Col>
        </Row>
      </Col>
      <Col
        span={24}
        css={css`
          height: 48px;
          display: flex;
          color: ${theme.colorTextSecondary};
          align-items: center;
        `}
      >
        <Description.Container>
          <Description.Item description={photon.model} />
        </Description.Container>
      </Col>
      <Col span={24}>
        <Description.Container
          css={css`
            font-size: 12px;
          `}
        >
          <Tag color={relatedDeployments.length > 0 ? "success" : "default"}>
            <Description.Item
              icon={<DeploymentIcon />}
              description={
                <PopoverDeploymentTable
                  photon={photon}
                  deployments={relatedDeployments}
                />
              }
            />
          </Tag>
          <Description.Item
            icon={<CarbonIcon icon={<Time />} />}
            description={
              <Link to={`/photons/detail/${photon.id}`} relative="route">
                <DataParser prefix="Updated" date={photon.created_at} />
              </Link>
            }
          />
          <Description.Item
            icon={<CarbonIcon icon={<Version />} />}
            description={
              <Link to={`/photons/versions/${photon.name}`} relative="route">
                {photon.versions.length}{" "}
                {photon.versions.length > 1 ? "versions" : "version"}
              </Link>
            }
          />
        </Description.Container>
      </Col>
    </Row>
  ) : (
    <></>
  );
};
