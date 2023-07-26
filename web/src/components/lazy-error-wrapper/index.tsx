import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { Loading } from "@lepton-dashboard/components/loading";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { EventTrackerService } from "@lepton-dashboard/services/event-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Button, Typography } from "antd";
import { LazyExoticComponent, ReactElement, Suspense } from "react";
import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  eventTrackerService: EventTrackerService;
}

interface State {
  hasError: boolean;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  private eventTrackerService: EventTrackerService;

  public static getDerivedStateFromError(_: Error): State {
    return { hasError: true };
  }

  constructor(props: Props) {
    super(props);
    this.eventTrackerService = props.eventTrackerService;
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.eventTrackerService.track("JS_ERROR", {
      componentStack: errorInfo.componentStack,
      error: error.message,
    });
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <CenterBox>
          <Typography.Title
            level={2}
            css={css`
              margin-top: 0;
            `}
          >
            Under maintenance
          </Typography.Title>
          <Typography.Paragraph>
            The page is down for maintenance, we are working to get it back as
            soon as possible.
          </Typography.Paragraph>
          <Button block type="primary" onClick={() => location.reload()}>
            Try again
          </Button>
        </CenterBox>
      );
    }
    return this.props.children;
  }
}

export const lazyErrorWrapper = (
  Component: LazyExoticComponent<SafeAny>
): (() => ReactElement) => {
  return () => {
    const eventTrackerService = useInject(EventTrackerService);
    return (
      <ErrorBoundary eventTrackerService={eventTrackerService}>
        <Suspense fallback={<Loading />}>
          <Component />
        </Suspense>
      </ErrorBoundary>
    );
  };
};
