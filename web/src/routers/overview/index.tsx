import { FC } from "react";
import styled from "@emotion/styled";
import { Metrics } from "@lepton-dashboard/routers/overview/components/metrics";
import { Dashboard } from "@lepton-dashboard/routers/overview/components/dashboard";

const Container = styled.div``;
export const Overview: FC = () => {
  return (
    <Container>
      <Metrics />
      <Dashboard />
    </Container>
  );
};
