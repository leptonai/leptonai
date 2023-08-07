import { WatsonHealth3DSoftware } from "@carbon/icons-react";
import { FC, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Col, Empty, Row, Timeline } from "antd";
import { BreadcrumbHeader } from "../../../../../../components/breadcrumb-header";
import { Card } from "@lepton-dashboard/components/card";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { PhotonItem } from "../../../../../../components/photon-item";
import { PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { take } from "rxjs";

export const Versions: FC = () => {
  const { name } = useParams();
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const navigateService = useInject(NavigateService);
  const photons = useStateFromObservable(
    () => photonService.listByName(name!),
    []
  );
  const versions: PhotonVersion[] = useMemo(() => {
    return photons.map(({ id, created_at }) => ({ id, created_at }));
  }, [photons]);

  const onDeleted = () => {
    photonService
      .listByName(name!)
      .pipe(take(1))
      .subscribe((photons) => {
        if (photons.length === 0) {
          navigateService.navigateTo("photonsList");
        }
      });
  };

  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader
          items={[
            {
              title: (
                <>
                  <PhotonIcon />
                  <LinkTo name="photonsList">
                    <span>Photons</span>
                  </LinkTo>
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
          <PhotonItem
            photon={photons[0]}
            versions={versions}
            allowDeleteAllVersions
            onDeleted={onDeleted}
          />
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Versions">
          {photons.length > 0 ? (
            <Timeline
              css={css`
                padding: 8px 0;
              `}
              items={photons.map((m) => {
                return {
                  key: m.id,
                  color: theme.colorTextSecondary,
                  dot: <WatsonHealth3DSoftware />,
                  children: (
                    <Card
                      css={css`
                        position: relative;
                        top: -1px;
                      `}
                      shadowless
                      paddingless
                      borderless
                    >
                      <PhotonItem photon={m} onDeleted={onDeleted} showDetail />
                    </Card>
                  ),
                };
              })}
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="No versions found"
            />
          )}
        </Card>
      </Col>
    </Row>
  );
};
