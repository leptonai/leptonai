import { CheckCircleFilled } from "@ant-design/icons";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  CodeBlock,
  LanguageSupports,
} from "@lepton-dashboard/routers/workspace/components/code-block";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Collapse, Typography } from "antd";
import { FC } from "react";

export const GettingStarted: FC<{ finished?: boolean }> = ({ finished }) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const credential = [
    workspaceTrackerService.id,
    workspaceTrackerService.workspace?.auth.token,
  ]
    .filter((x) => x)
    .join(":");

  const theme = useAntdTheme();

  const extra = finished ? (
    <CheckCircleFilled
      css={css`
        color: ${theme.colorSuccess};
      `}
    />
  ) : null;
  const maskCredential = (content: string) => {
    if (
      content.includes(credential) &&
      workspaceTrackerService.workspace?.auth.token
    ) {
      return `${workspaceTrackerService.id}:${"*".repeat(
        workspaceTrackerService.workspace?.auth.token?.length ?? 0
      )}`;
    } else {
      return false;
    }
  };
  return (
    <div>
      <Typography.Title
        level={3}
        css={css`
          margin-top: 0;
        `}
      >
        Getting Started
      </Typography.Title>
      <Typography.Paragraph>
        Welcome to Lepton AI! Let's start by setting up Lepton on your local
        machine, and run a classical AI model: GPT-2.
      </Typography.Paragraph>
      <Collapse
        items={[
          {
            key: "1",
            extra,
            label: "Install Python client",
            children: (
              <>
                <Typography.Paragraph>
                  Install the python package from PyPI. Assuming you are using{" "}
                  <Typography.Text code>pip</Typography.Text>, do the following:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="pip install --pre -U leptonai"
                    copyable={true}
                    language={LanguageSupports.Bash}
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  Closed beta note: this will later be a direct pypi install but
                  we are hosting on S3 for now for beta testing.
                </Typography.Paragraph>
                <Typography.Paragraph>
                  You can check that it is installed by running:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="lep --help"
                    copyable={true}
                    language={LanguageSupports.Bash}
                  />
                </Typography.Paragraph>
              </>
            ),
          },
          {
            key: "2",
            extra,
            label: "Build and run locally",
            children: (
              <>
                <Typography.Paragraph>
                  Lepton uses the concept of a{" "}
                  <Typography.Text code>photon</Typography.Text> to bundle the
                  code to run an AI model, its dependencies, etc. For now, let's
                  create a photon for GPT-2:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="lep photon create --name mygpt2 --model hf:gpt2"
                    language={LanguageSupports.Bash}
                    copyable
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  This creates a photon named{" "}
                  <Typography.Text code>mygpt2</Typography.Text>. We'll go into
                  the details of what a photon is later, but for now, it is
                  readily runnable locally. Let's run it:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="lep photon run --name mygpt2 --local"
                    language={LanguageSupports.Bash}
                    copyable
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  This starts a local server running the gpt2 model, you can try
                  it out via cURL
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code={`curl -X 'POST' \\
  'http://0.0.0.0:8080/run' \\
  -H 'accept: application/json' \\
  -H 'Content-Type: application/json' \\
  -d '{
  "inputs": "Once upon a time"
}'`}
                    language={LanguageSupports.Bash}
                    copyable
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  The running photon also exposes HTML websites for more
                  detailed inspections. More specifically, you may visit{" "}
                  <Typography.Link
                    href="http://0.0.0.0:8080/docs"
                    target="_blank"
                  >
                    http://0.0.0.0:8080/docs
                  </Typography.Link>{" "}
                  to inspect the docs, and make a call via the web UI.
                </Typography.Paragraph>
                <Typography.Paragraph>
                  For machine learning models, the first run is usually a bit
                  slower than later runs, as the underlying runtime (in this
                  case pytorch) may have a few intial setup steps such as memory
                  allocation and compilation. Subsequent runs would be much
                  faster - this is a common pattern.
                </Typography.Paragraph>
              </>
            ),
          },
          {
            key: "3",
            extra,
            label: "Deploy in the cloud",
            children: (
              <>
                <Typography.Paragraph>
                  To do this, let's first log in to the Lepton cloud from CLI.
                  Login with
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code={`lep login -c ${credential}`}
                    tokenMask={maskCredential}
                    language={LanguageSupports.Bash}
                    copyable
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  Once we are successfully logged in, let's push the locally
                  built photon, mygpt2, to your workspace:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="lep photon push --name mygpt2"
                    language={LanguageSupports.Bash}
                    copyable
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  Once the photon is pushed, we can create a deployment, which
                  is a running instance of a photon on the cloud:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="lep photon run --name mygpt2 --deployment-name mygpt2"
                    language={LanguageSupports.Bash}
                    copyable
                  />
                </Typography.Paragraph>
                <Typography.Paragraph>
                  Note that we are not using the --local flag this time. When we
                  are logged in, this tells Lepton to run the photon on the
                  cloud, instead of locally. For the sake of simplicity we named
                  the deployment the same as the photon, but you can name it
                  anything you want.
                </Typography.Paragraph>
                <Typography.Paragraph>
                  Now, go to the deployment tab on the top of the page, and try
                  it out! For more details on how to use other features of
                  Lepton, please refer to the{" "}
                  <Typography.Link
                    href="https://lepton.ai/docs"
                    target="_blank"
                  >
                    Lepton documentation
                  </Typography.Link>
                  .
                </Typography.Paragraph>
              </>
            ),
          },
        ]}
        defaultActiveKey={finished ? ["3"] : ["1"]}
      />
      <Typography.Paragraph
        css={css`
          margin-top: 1em;
        `}
      >
        Congratulations on completing all the tutorials. Learn more by visiting
        the{" "}
        <Typography.Link href="https://lepton.ai/docs" target="_blank">
          documentation page.
        </Typography.Link>
      </Typography.Paragraph>
    </div>
  );
};
