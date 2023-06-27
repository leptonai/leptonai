import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { FC, useEffect, useRef, useState } from "react";
import { Button } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Terminal as CarbonTerminal } from "@carbon/icons-react";
import { Deployment, Replica } from "@lepton-dashboard/interfaces/deployment";
import { FullScreenDrawer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/components/full-screen-drawer";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FitAddon } from "xterm-addon-fit";
import { AttachAddon } from "xterm-addon-attach";
import { css } from "@emotion/react";
import { Terminal as Xterm } from "xterm";
import "xterm/css/xterm.css";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";

export const TerminalDetail: FC<{
  deploymentId: string;
  replicaId: string;
}> = ({ deploymentId, replicaId }) => {
  const theme = useAntdTheme();
  const terminalDOMRef = useRef<HTMLDivElement>(null);
  const deploymentService = useInject(DeploymentService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  useEffect(() => {
    const term = new Xterm({
      fontFamily: theme.fontFamilyCode,
      theme: {
        foreground: "#f8f8f2",
        background: "#1e1f29",
        cursor: "#bbbbbb",

        black: "#000000",
        brightBlack: "#555555",

        red: "#ff5555",
        brightRed: "#ff5555",

        green: "#50fa7b",
        brightGreen: "#50fa7b",

        yellow: "#f1fa8c",
        brightYellow: "#f1fa8c",

        blue: "#2F80ED",
        brightBlue: "#2D9CDB",

        magenta: "#ff79c6",
        brightMagenta: "#ff79c6",

        cyan: "#8be9fd",
        brightCyan: "#8be9fd",

        white: "#bbbbbb",
        brightWhite: "#ffffff",
      },
    });
    const socket = new WebSocket(
      deploymentService.getReplicaSocketUrl(
        workspaceTrackerService.cluster!.auth.url,
        deploymentId,
        replicaId
      ),
      "v4.channel.k8s.io"
    );
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new AttachAddon(socket));
    term.open(terminalDOMRef.current!);
    term.focus();
    socket.onopen = () => {
      fitAddon.fit();
      term.writeln(
        [
          "========================================================",
          "    _     _____ ____ _____ ___  _   _       _    ___     ",
          "   | |   | ____|  _ \\_   _/ _ \\| \\ | |     / \\  |_ _|    ",
          "   | |   |  _| | |_) || || | | |  \\| |    / _ \\  | |     ",
          "   | |___| |___|  __/ | || |_| | |\\  |   / ___ \\ | |     ",
          "   |_____|_____|_|    |_| \\___/|_| \\_|  /_/   \\_\\___|    ",
          "                                                         ",
          "========================================================",
        ]
          .map((s) => {
            return s
              .split("")
              .map((char) => {
                if (char === "=") {
                  return char;
                } else {
                  return `\x1b[34m${char}\x1b[0m`;
                }
              })
              .join("");
          })
          .join("\n\r")
      );
      term.writeln("\n\r");
    };
    term.onData((data) => {
      const encoder = new TextEncoder();
      socket.send(encoder.encode(`\x00${data}`));
    });
    socket.onclose = () => {
      term.writeln(
        "\n\r\n\r\x1b[31mConnection lost, please reconnect\x1b[0m\n\r"
      );
    };
    return () => {
      term.dispose();
      socket.close();
    };
  }, [
    deploymentId,
    deploymentService,
    replicaId,
    theme.fontFamilyCode,
    workspaceTrackerService.cluster,
  ]);
  return (
    <div
      css={css`
        height: 100%;
        width: 100%;
        padding: 12px;
        background: #1e1f29;
      `}
      ref={terminalDOMRef}
    />
  );
};
export const Terminal: FC<{
  deployment: Deployment;
  replica: Replica;
}> = ({ deployment, replica }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        icon={<CarbonIcon icon={<CarbonTerminal />} />}
        type="text"
        onClick={() => setOpen(true)}
        size="small"
      >
        Terminal
      </Button>
      <FullScreenDrawer open={open} onClose={() => setOpen(false)}>
        <TerminalDetail deploymentId={deployment.id} replicaId={replica.id} />
      </FullScreenDrawer>
    </>
  );
};
