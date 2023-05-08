import { FC, useMemo } from "react";
import { GroupedPhoton } from "@lepton-dashboard/interfaces/photon.ts";
import { Button, Divider, Popover, Space } from "antd";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { DockerIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
import dayjs from "dayjs";
import { RocketOutlined } from "@ant-design/icons";
import { Link } from "@lepton-dashboard/components/link";
import { Hoverable } from "@lepton-dashboard/components/hoverable";
import { DetailDescription } from "@lepton-dashboard/routers/photons/components/detail-description";
import { Card } from "@lepton-dashboard/components/card";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useNavigate } from "react-router-dom";

const Container = styled.div`
  display: flex;
`;
const Left = styled.div`
  flex: 1 1 auto;
  max-width: 600px;
  padding-right: 12px;
`;
const Right = styled.div`
  flex: 0 0 100px;
`;
const DockerDetail = styled.div`
  width: 400px;
`;
export const PhotonGroupCard: FC<{
  group: GroupedPhoton;
  deploymentCount: number;
  shadowless?: boolean;
}> = ({ group, deploymentCount, shadowless = false }) => {
  const photon = group.latest;
  const theme = useAntdTheme();
  const navigate = useNavigate();
  const Title = useMemo(
    () => styled.div`
      font-size: 16px;
      font-weight: 500;
      color: ${theme.colorTextHeading};
    `,
    [theme]
  );
  const PhotonSource = useMemo(
    () => styled.div`
      font-size: 14px;
      color: ${theme.colorTextSecondary};
      margin: 12px 0;
    `,
    [theme]
  );
  const Description = useMemo(
    () => styled.div`
      font-size: 12px;
      white-space: nowrap;
      color: ${theme.colorTextDescription};
    `,
    [theme]
  );
  return (
    <Card shadowless={shadowless}>
      <Container>
        <Left>
          <Title>
            <Link
              icon={<PhotonIcon />}
              to={`/photons/versions/${photon.name}`}
              relative="route"
            >
              {photon.name}
            </Link>
          </Title>
          <PhotonSource>
            <Space>
              <Popover
                placement="bottomLeft"
                content={
                  <DockerDetail>
                    <ThemeProvider token={{ fontSize: 12 }}>
                      <DetailDescription photon={photon} />
                    </ThemeProvider>
                  </DockerDetail>
                }
              >
                <span>
                  <Hoverable>
                    <DockerIcon />
                  </Hoverable>
                </span>
              </Popover>
              {photon.model || "-"}
            </Space>
          </PhotonSource>
        </Left>
        <Right>
          <Button
            onClick={() =>
              navigate(`/deployments/create/${photon.id}`, {
                relative: "route",
              })
            }
            icon={<RocketOutlined />}
          >
            Deploy
          </Button>
        </Right>
      </Container>

      <Space size={0} split={<Divider type="vertical" />}>
        <Description>
          <Link to={`/photons/detail/${photon.id}`} relative="route">
            Updated {dayjs(photon.created_at).format("ll")}
          </Link>
        </Description>
        <Description>
          <Link to={`/photons/versions/${photon.name}`} relative="route">
            {group.data.length > 1
              ? `${group.data.length} versions`
              : "1 version"}
          </Link>
        </Description>
        <Description>
          <Link to={`/deployments/list/${photon.name}`} relative="route">
            {deploymentCount} deployments
          </Link>
        </Description>
      </Space>
    </Card>
  );
};
