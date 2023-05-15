import { FC } from "react";
import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon.ts";
import { Description } from "../description";
import { DateParser } from "../date-parser";
import { App, Button, Col, Divider, Empty, Popconfirm, Row, Space } from "antd";
import { Link } from "@lepton-dashboard/components/link";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  Column,
  ContainerRegistry,
  Download,
  Link as CarbonLink,
  Parameter,
  PortOutput,
  Time,
  TransformBinary,
  Version,
  WorkspaceImport,
} from "@carbon/icons-react";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { useNavigate } from "react-router-dom";
import { PopoverDeploymentTable } from "@lepton-dashboard/components/refactor/popover-deployment-table";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { DeleteOutlined } from "@ant-design/icons";

const PhotonExtraInfo: FC<{ photon: Photon; versionView: boolean }> = ({
  photon,
  versionView,
}) => {
  const theme = useAntdTheme();
  return (
    <Col
      span={24}
      css={css`
        color: ${theme.colorTextDescription};
        font-size: 12px;
      `}
    >
      <Description.Item
        icon={<CarbonIcon icon={<Column />} />}
        term="ID"
        description={
          <Link to={`/photons/detail/${photon.id}`}>{photon.id}</Link>
        }
      />
      {versionView && (
        <Description.Item
          icon={<CarbonIcon icon={<TransformBinary />} />}
          term="Model"
          description={photon.model}
        />
      )}
      <Description.Item
        icon={<CarbonIcon icon={<Parameter />} />}
        term="Arguments"
        description={photon.container_args?.join(", ") || "-"}
      />
      <Description.Item
        icon={<CarbonIcon icon={<ContainerRegistry />} />}
        term="Requirements"
        description={photon.requirement_dependency?.join(", ") || "-"}
      />
      <Description.Item
        icon={<CarbonIcon icon={<WorkspaceImport />} />}
        term="Entrypoint"
        description={photon.entrypoint || "-"}
      />
      <Description.Item
        term="Exposed Ports"
        icon={<CarbonIcon icon={<PortOutput />} />}
        description={photon.exposed_ports?.join(", ") || "-"}
      />
      <Description.Item
        term="Image URL"
        icon={<CarbonIcon icon={<CarbonLink />} />}
        description={photon.image || "-"}
      />
    </Col>
  );
};

const PhotonVersions: FC<{ versions: PhotonVersion[]; photon: Photon }> = ({
  versions,
  photon,
}) => {
  return (
    <Description.Item
      icon={<CarbonIcon icon={<Version />} />}
      description={
        <Link to={`/photons/versions/${photon.name}`} relative="route">
          {versions.length} {versions.length > 1 ? "versions" : "version"}
        </Link>
      }
    />
  );
};

const PhotonTime: FC<{
  versions?: PhotonVersion[];
  photon: Photon;
  detail: boolean;
}> = ({ versions, photon }) => {
  return (
    <Description.Item
      icon={<CarbonIcon icon={<Time />} />}
      description={
        <Link to={`/photons/detail/${photon.id}`} relative="route">
          <DateParser
            prefix={versions && versions.length > 1 ? "Updated" : "Created"}
            date={photon.created_at}
          />
        </Link>
      }
    />
  );
};

const PhotonActions: FC<{ photon: Photon; extraActions: boolean }> = ({
  photon,
  extraActions = false,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  return (
    <Col flex="0 0 auto">
      <Space size={0} split={<Divider type="vertical" />}>
        <Button
          size="small"
          type="text"
          icon={<DeploymentIcon />}
          onClick={() =>
            navigate(`/deployments/create/${photon.id}`, {
              relative: "route",
            })
          }
        >
          Deploy
        </Button>
        {extraActions && (
          <>
            <Button
              icon={<CarbonIcon icon={<Download />} />}
              type="text"
              size="small"
              href={photonService.getDownloadUrlById(photon.id)}
              download
            >
              Download
            </Button>
            <Popconfirm
              title="Delete the photon"
              description="Are you sure to delete?"
              onConfirm={() => {
                void message.loading({
                  content: `Deleting photon ${photon.id}, please wait...`,
                  key: "delete-photon",
                  duration: 0,
                });
                photonService.delete(photon.id).subscribe({
                  next: () => {
                    message.destroy("delete-photon");
                    void message.success(
                      `Successfully deleted photon ${photon.id}`
                    );
                    refreshService.refresh();
                  },
                  error: () => {
                    message.destroy("delete-photon");
                  },
                });
              }}
            >
              <Button danger size="small" type="text" icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          </>
        )}
      </Space>
    </Col>
  );
};
export const PhotonItem: FC<{
  photon?: Photon;
  versions?: PhotonVersion[];
  versionView?: boolean;
  showDetail?: boolean;
  extraActions?: boolean;
}> = ({
  photon,
  versions,
  versionView = false,
  showDetail = false,
  extraActions = false,
}) => {
  const theme = useAntdTheme();
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const relatedDeployments = deployments.filter((d) => {
    if (versions) {
      return versions.some((v) => v.id === d.photon_id);
    } else {
      return d.photon_id === photon?.id;
    }
  });
  return photon ? (
    <Row wrap={false}>
      <Col flex="1 1 auto">
        <Row>
          {!versionView && (
            <Col span={24}>
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
          )}
          <Col span={24}>
            <Row gutter={[0, 16]}>
              <Col span={24}>
                <Row>
                  {!versionView && (
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
                  )}
                  <Col span={24}>
                    <Description.Container
                      css={css`
                        font-size: 12px;
                      `}
                    >
                      <PopoverDeploymentTable
                        photon={photon}
                        deployments={relatedDeployments}
                      />
                      {!versionView && (
                        <PhotonTime
                          detail={showDetail}
                          photon={photon}
                          versions={versions}
                        />
                      )}
                      {versions && !showDetail && (
                        <PhotonVersions photon={photon} versions={versions} />
                      )}
                    </Description.Container>
                  </Col>
                </Row>
              </Col>

              {showDetail && (
                <PhotonExtraInfo versionView={versionView} photon={photon} />
              )}
            </Row>
          </Col>
        </Row>
      </Col>
      <PhotonActions photon={photon} extraActions={extraActions} />
    </Row>
  ) : (
    <Empty />
  );
};
