import { FC, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Col, Row, Timeline, Typography } from "antd";
import { Link } from "@lepton-dashboard/components/link";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/photons/components/breadcrumb-header";
import { Card } from "@lepton-dashboard/components/card";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import dayjs from "dayjs";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { PhotonItem } from "../../../../components/photon-item";
import { PhotonVersion } from "@lepton-dashboard/interfaces/photon.ts";

export const Versions: FC = () => {
  const { name } = useParams();
  const photonService = useInject(PhotonService);
  const photons = useStateFromObservable(
    () => photonService.listByName(name!),
    []
  );
  const versions: PhotonVersion[] = useMemo(() => {
    return photons.map(({ id, created_at }) => ({ id, created_at }));
  }, [photons]);
  const theme = useAntdTheme();
  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader
          items={[
            {
              title: (
                <>
                  <PhotonIcon />
                  <Link to="../../photons">
                    <span>Photons</span>
                  </Link>
                </>
              ),
            },
            {
              title: name,
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card>
          <PhotonItem photon={photons[0]} versions={versions} />
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Version History">
          <Timeline
            css={css`
              padding: 8px 0;
            `}
            items={photons.map((m) => {
              return {
                key: m.id,
                color: theme.colorTextSecondary,
                dot: <PhotonIcon />,
                children: (
                  <Col key={m.id} span={24}>
                    <Typography.Paragraph
                      style={{ paddingTop: "1px" }}
                      type="secondary"
                    >
                      Created at {dayjs(m.created_at).format("lll")}
                    </Typography.Paragraph>
                    <Card shadowless>
                      <PhotonItem
                        versionView
                        extraActions
                        photon={m}
                        showDetail
                      />
                    </Card>
                  </Col>
                ),
              };
            })}
          />
        </Card>
      </Col>
    </Row>
  );
};
