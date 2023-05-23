import { FC, memo, useRef, useState } from "react";
import { Button, Spin } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { DataViewAlt } from "@carbon/icons-react";
import {
  Deployment,
  Instance,
} from "@lepton-dashboard/interfaces/deployment.ts";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import Editor from "@monaco-editor/react";
import { FullScreenDrawer } from "@lepton-dashboard/routers/deployments/components/full-screen-drawer";
import { css } from "@emotion/react";
import type { editor as MonacoEditor } from "monaco-editor";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

const LogDetail: FC<{
  deploymentId: string;
  instanceId: string;
}> = memo(
  ({ deploymentId, instanceId }) => {
    const theme = useAntdTheme();
    const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
    const isFocusRef = useRef(false);
    const [loading, setLoading] = useState(true);
    const deploymentService = useInject(DeploymentService);
    const logs = useStateFromObservable(
      () => deploymentService.getInstanceLog(deploymentId, instanceId),
      "",
      {
        next: () => {
          setLoading(false);
          const editor = editorRef.current;
          if (editor && !isFocusRef.current) {
            const lineCount = editor.getModel()!.getLineCount();
            editor.revealLine(lineCount, 0);
          }
        },
        error: () => setLoading(false),
      }
    );

    return loading ? (
      <div
        css={css`
          height: 100%;
          width: 100%;
          background: ${theme.colorBgContainer};
          display: flex;
          align-items: center;
          justify-content: center;
        `}
      >
        <Spin tip="Loading ..." />
      </div>
    ) : (
      <Editor
        onMount={(editor) => {
          editorRef.current = editor;
          editor.onDidFocusEditorText(() => (isFocusRef.current = true));
        }}
        theme="lepton"
        loading={<Spin />}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
        }}
        height="100%"
        value={logs}
      />
    );
  },
  () => true
);

export const LogsViewer: FC<{
  deployment: Deployment;
  instance: Instance;
}> = ({ deployment, instance }) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        icon={<CarbonIcon icon={<DataViewAlt />} />}
        type="text"
        size="small"
      >
        Logs
      </Button>
      <FullScreenDrawer open={open} onClose={() => setOpen(false)}>
        <LogDetail deploymentId={deployment.id} instanceId={instance.id} />
      </FullScreenDrawer>
    </>
  );
};
