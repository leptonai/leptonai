import { FC, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Breadcrumb, Col, List as AntdList, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/photons/components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { PhotonCard } from "@lepton-dashboard/components/photon-card";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";
import { PhotonIcon } from "@lepton-dashboard/components/icons";

export const Detail: FC = () => {
  const { id } = useParams();
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(() => photonService.id(id!), undefined);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const filteredDeployments = useMemo(() => {
    return deployments.filter((d) => d.photon_id === id);
  }, [deployments, id]);

  return photon ? (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader>
          <Breadcrumb
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
                  <Link to={`../../versions/${photon.name}`}>
                    {photon.name}
                  </Link>
                ),
              },
              {
                title: photon.id,
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>
      <Col span={24}>
        <Card title="Photon Detail">
          <PhotonCard
            paddingless
            borderless
            shadowless
            photon={photon}
            detail={true}
          />
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Deployments" paddingless>
          <AntdList
            itemLayout="horizontal"
            dataSource={filteredDeployments}
            renderItem={(deployment) => (
              <AntdList.Item style={{ padding: 0, display: "block" }}>
                <DeploymentCard photonPage deployment={deployment} borderless />
              </AntdList.Item>
            )}
          />
        </Card>
      </Col>
    </Row>
  ) : null;
};
