import { FC } from "react";
import styled from "@emotion/styled";
import {
  AppstoreOutlined,
  ExperimentOutlined,
  InteractionOutlined,
} from "@ant-design/icons";
import { RouterLink } from "@lepton-dashboard/components/layout/components/nav/components/router-link";
const Container = styled.nav`
  margin-top: 24px;
  flex: 1 1 auto;
`;

export const Nav: FC = () => {
  return (
    <Container>
      <RouterLink link="overview" text="Overview" icon={<AppstoreOutlined />} />
      <RouterLink link="models" text="Models" icon={<ExperimentOutlined />} />
      <RouterLink
        link="deployments"
        text="Deployments"
        icon={<InteractionOutlined />}
      />
    </Container>
  );
};
