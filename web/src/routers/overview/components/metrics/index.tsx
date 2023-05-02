import { FC } from "react";
import { Section } from "@lepton-dashboard/components/section";
import {
  Card,
  CardContainer,
} from "@lepton-dashboard/routers/overview/components/metrics/components/card";
import {
  BuildOutlined,
  ExperimentOutlined,
  InteractionOutlined,
} from "@ant-design/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const Metrics: FC = () => {
  const theme = useAntdTheme();
  return (
    <Section title="Metrics">
      <CardContainer>
        <Card
          color={theme.colorPrimaryBg}
          title="Total Requests"
          icon={<BuildOutlined />}
          data={56569}
        />
        <Card
          color={theme.colorWarningBg}
          title="Models"
          icon={<ExperimentOutlined />}
          data={1}
        />
        <Card
          color={theme.colorSuccessBg}
          title="Deployments"
          icon={<InteractionOutlined />}
          data={20}
        />
      </CardContainer>
    </Section>
  );
};
