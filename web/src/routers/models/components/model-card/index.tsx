import { FC, useMemo } from "react";
import { GroupedModel } from "@lepton-dashboard/interfaces/model.ts";
import { Button, Divider, Popover, Space } from "antd";
import styled from "@emotion/styled";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { DockerIcon } from "@lepton-dashboard/components/icons/logo";
import dayjs from "dayjs";
import { RocketOutlined } from "@ant-design/icons";
import { Link } from "@lepton-dashboard/components/link";
import { Hoverable } from "@lepton-dashboard/components/hoverable";
import { DetailDescription } from "@lepton-dashboard/routers/models/components/detail-description";
import { Card } from "@lepton-dashboard/components/card";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useNavigate } from "react-router-dom";

const Left = styled.div`
  flex: 1 1 auto;
`;
const Right = styled.div`
  flex: 0 0 100px;
`;
const DockerDetail = styled.div`
  width: 400px;
`;
export const ModelCard: FC<{ group: GroupedModel }> = ({ group }) => {
  const model = group.latest;
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
  const ModelSource = useMemo(
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
    <Card direction="horizontal">
      <Left>
        <Title>
          <Link to={`../versions/${group.name}`}>{model.name}</Link>
        </Title>
        <ModelSource>{model.model_source}</ModelSource>
        <Space size={0} split={<Divider type="vertical" />}>
          <Popover
            placement="bottomLeft"
            content={
              <DockerDetail>
                <ThemeProvider token={{ fontSize: 12 }}>
                  <DetailDescription model={model} />
                </ThemeProvider>
              </DockerDetail>
            }
          >
            <Description>
              <Hoverable>
                <DockerIcon />
              </Hoverable>
            </Description>
          </Popover>
          <Description>
            <Link to={`../detail/${model.id}`}>
              Updated {dayjs(model.created_at).format("ll")}
            </Link>
          </Description>
          <Description>
            <Link to={`../versions/${group.name}`}>
              {group.data.length > 1
                ? `${group.data.length} versions`
                : "1 version"}
            </Link>
          </Description>
        </Space>
      </Left>
      <Right>
        <Button
          onClick={() => navigate(`../../deployments/create/${model.id}`)}
          size="middle"
          icon={<RocketOutlined />}
        >
          Deploy
        </Button>
      </Right>
    </Card>
  );
};
