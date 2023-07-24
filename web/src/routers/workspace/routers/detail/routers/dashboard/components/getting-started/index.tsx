import { css } from "@emotion/react";
import {
  CodeBlock,
  LanguageSupports,
} from "@lepton-dashboard/routers/workspace/components/code-block";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Collapse, Typography } from "antd";
import { FC } from "react";

export const GettingStarted: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const credential = `${workspaceTrackerService.id}:${workspaceTrackerService.workspace?.auth.token}`;
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
            label: "Install Python client",
            children: (
              <>
                <Typography.Paragraph>
                  Install the python package from PyPI. Assuming you are using{" "}
                  <Typography.Text code>pip</Typography.Text>, do the following:
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code="pip install leptonai"
                    copyable={true}
                    language={LanguageSupports.Bash}
                  />
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
              </>
            ),
          },
          {
            key: "3",
            label: "Deploy in the cloud",
            children: (
              <>
                <Typography.Paragraph>
                  To do this, let's first log in to the Lepton cloud. Login with
                </Typography.Paragraph>
                <Typography.Paragraph>
                  <CodeBlock
                    code={`lep login -c ${credential}`}
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
              </>
            ),
          },
        ]}
        defaultActiveKey={["1"]}
      />
    </div>
  );
};
