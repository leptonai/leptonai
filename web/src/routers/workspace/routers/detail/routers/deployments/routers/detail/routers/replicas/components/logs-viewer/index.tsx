import { FC, memo, useRef, useState } from "react";
import { Button, Spin } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { DataViewAlt } from "@carbon/icons-react";
import { Deployment, Replica } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import Editor from "@monaco-editor/react";
import { css } from "@emotion/react";
import type { editor as MonacoEditor } from "monaco-editor";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FullScreenDrawer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/components/full-screen-drawer";

export const LogDetail: FC<{
  deploymentName: string;
  replicaId: string;
}> = memo(
  ({ deploymentName, replicaId }) => {
    const theme = useAntdTheme();
    const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
    const isFocusRef = useRef(false);
    const [loading, setLoading] = useState(true);
    const deploymentService = useInject(DeploymentService);
    const logs = useStateFromObservable(
      () => deploymentService.getReplicaLog(deploymentName, replicaId),
      "",
      {
        next: () => setLoading(false),
        error: () => setLoading(false),
      }
    );

    const scrollToLastLine = () => {
      const editor = editorRef.current;
      if (editor && !isFocusRef.current) {
        const lineCount = editor.getModel()!.getLineCount();
        editor.revealLine(lineCount, 1);
      }
    };

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
          scrollToLastLine();
        }}
        onChange={() => scrollToLastLine()}
        theme="lepton"
        loading={<Spin />}
        options={{
          overviewRulerLanes: 0,
          hideCursorInOverviewRuler: true,
          overviewRulerBorder: false,
          readOnly: true,
          wordWrap: "on",
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
  replica: Replica;
}> = ({ deployment, replica }) => {
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
        <LogDetail deploymentName={deployment.name} replicaId={replica.id} />
      </FullScreenDrawer>
    </>
  );
};
