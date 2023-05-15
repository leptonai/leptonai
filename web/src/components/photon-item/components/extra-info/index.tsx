import { FC } from "react";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Col } from "antd";
import { css } from "@emotion/react";
import { Description } from "@lepton-dashboard/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import {
  Column,
  ContainerRegistry,
  CopyLink,
  Link as CarbonLink,
  Parameter,
  PortOutput,
  WorkspaceImport,
} from "@carbon/icons-react";
import { Link } from "@lepton-dashboard/components/link";

export const ExtraInfo: FC<{ photon: Photon; versionView: boolean }> = ({
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
          icon={<CarbonIcon icon={<CopyLink />} />}
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
