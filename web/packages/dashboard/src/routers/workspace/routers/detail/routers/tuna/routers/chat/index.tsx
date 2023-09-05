import { css } from "@emotion/react";
import { Chats } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/chats";
import { benchmarkModel, ModelOption } from "@lepton/playground/shared/chat";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { FC } from "react";
import { useParams } from "react-router-dom";
import { Card } from "@lepton-dashboard/components/card";
import { map } from "rxjs";

export const Chat: FC = () => {
  const { name } = useParams();
  const tunaService = useInject(TunaService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const models = useStateFromObservable(
    () =>
      tunaService.listAvailableInferences().pipe(
        map((inference) => {
          return [
            benchmarkModel,
            ...inference
              .filter((i) => i.status?.api_endpoint)
              .map((i) => {
                return {
                  name: i.metadata.name,
                  apiOption: {
                    api_url: i.status?.api_endpoint,
                    api_key: workspaceTrackerService.workspace?.auth.token,
                  },
                };
              }),
          ] as ModelOption[];
        })
      ),
    []
  );
  if (models.length > 0) {
    return (
      <Card
        paddingless
        css={css`
          position: relative;
          width: 100%;
          flex: 1 1 auto;
        `}
      >
        <Chats baseName={name} models={models} />
      </Card>
    );
  } else {
    return (
      <Card
        css={css`
          width: 100%;
        `}
        loading
      />
    );
  }
};
