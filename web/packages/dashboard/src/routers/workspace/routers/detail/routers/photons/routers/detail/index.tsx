import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Col, Empty, Row } from "antd";
import { BreadcrumbHeader } from "../../../../../../components/breadcrumb-header";
import { Card } from "@lepton-dashboard/components/card";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { PhotonItem } from "../../../../../../components/photon-item";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { take } from "rxjs";

export const Detail: FC = () => {
  const { id } = useParams();
  const photonService = useInject(PhotonService);
  const navigateService = useInject(NavigateService);
  const photon = useStateFromObservable(() => photonService.id(id!), undefined);

  const onDeleted = (name: string) => {
    photonService
      .listByName(name)
      .pipe(take(1))
      .subscribe((photons) => {
        if (photons.length === 0) {
          navigateService.navigateTo("photonsList");
        } else {
          navigateService.navigateTo("photonVersions", {
            name: name,
          });
        }
      });
  };

  return photon ? (
    <Row gutter={[0, 16]}>
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
              title: (
                <LinkTo name="photonVersions" params={{ name: photon.name }}>
                  {photon.name}
                </LinkTo>
              ),
            },
            {
              title: photon.id,
            },
          ]}
        />
      </Col>
      <Col span={24}>
        <Card>
          <PhotonItem onDeleted={onDeleted} photon={photon} showDetail />
        </Card>
      </Col>
    </Row>
  ) : (
    <Card>
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="No photon found"
      />
    </Card>
  );
};
