import { FC } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Col, Row } from "antd";
import { BreadcrumbHeader } from "../../../../components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { Card } from "@lepton-dashboard/components/card";
import { PhotonIcon } from "@lepton-dashboard/components/icons";
import { PhotonItem } from "../../../../components/photon-item";

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
                  <Link to="../../photons">
                    <span>Photons</span>
                  </Link>
                </>
              ),
            },
            {
              title: (
                <Link to={`../../versions/${photon.name}`}>{photon.name}</Link>
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
          <PhotonItem photon={photon} showDetail extraActions />
        </Card>
      </Col>
    </Row>
  ) : null;
};
