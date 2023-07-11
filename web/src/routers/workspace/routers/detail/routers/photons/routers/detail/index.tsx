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

export const Detail: FC = () => {
  const { id } = useParams();
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(() => photonService.id(id!), undefined);
  return photon ? (
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
              title: (
                <LinkTo
                  name="photonVersions"
                  params={{ photonId: photon.name }}
                >
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
          <PhotonItem photon={photon} showDetail />
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
