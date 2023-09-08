import { css } from "@emotion/react";
import { CenterBox } from "@lepton-dashboard/components/center-box";
import { Loading } from "@lepton-dashboard/components/loading";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { Button, Typography } from "antd";
import { LazyExoticComponent, ReactElement, Suspense } from "react";
import { ErrorBoundary } from "@highlight-run/react";

export const lazyErrorWrapper = (
  Component: LazyExoticComponent<SafeAny>
): (() => ReactElement) => {
  return () => {
    return (
      <ErrorBoundary
        showDialog={false}
        fallback={
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
        }
      >
        <Suspense fallback={<Loading />}>
          <Component />
        </Suspense>
      </ErrorBoundary>
    );
  };
};
