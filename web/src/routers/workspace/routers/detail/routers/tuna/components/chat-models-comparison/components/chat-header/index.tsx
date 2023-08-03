import { FC, useCallback, useEffect, useMemo, useState } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { TunaService } from "@lepton-dashboard/routers/workspace/services/tuna.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map, of, switchMap } from "rxjs";
import { css } from "@emotion/react";
import { Button, Popover, Select, Space } from "antd";
import { ApiModal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/components/api-modal";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Code, Erase } from "@carbon/icons-react";
import {
  benchmarkModel,
  ChatCompletion,
  ModelOption,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/tuna/services/chat.service";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
export const ChatHeader: FC<{
  modelName: string;
  onModelChange: (option: ModelOption) => void;
  chat?: ChatCompletion | null;
}> = ({ modelName, onModelChange, chat }) => {
  const theme = useAntdTheme();
  const tunaService = useInject(TunaService);
  const [value, setValue] = useState(benchmarkModel.name);
  const [loading, setLoading] = useState(true);
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
                  },
                };
              }),
          ] as ModelOption[];
        })
      ),
    [benchmarkModel],
    {
      next: () => {
        setLoading(false);
      },
      error: () => {
        setLoading(false);
      },
    }
  );

  const onChange = useCallback(
    (value: string) => {
      const model = models.find((m) => m.name === value);
      if (model) {
        setValue(value);
        onModelChange(model);
      }
    },
    [models, onModelChange]
  );

  useEffect(() => {
    if (loading) {
      return;
    }
    const model = models.find((m) => m.name === modelName);
    if (model) {
      onChange(model.name);
    } else {
      onChange(benchmarkModel.name);
    }
  }, [modelName, models, onChange, loading]);

  const model = useMemo(() => {
    return models.find((m) => m.name === value);
  }, [models, value]);

  const chat$ = useObservableFromState(chat);
  const messages = useStateFromObservable(
    () =>
      chat$.pipe(
        switchMap((instance) =>
          instance ? instance.onMessagesChanged() : of([])
        )
      ),
    []
  );
  const generating = useStateFromObservable(
    () =>
      chat$.pipe(
        switchMap((instance) =>
          instance ? instance.onGeneratingChanged() : of(false)
        )
      ),
    false
  );

  const clear = useCallback(() => {
    chat?.clear();
  }, [chat]);

  return (
    <div
      css={css`
        padding: ${theme.paddingSM}px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      `}
    >
      <div>
        <Select
          disabled={loading}
          loading={loading}
          css={css`
            width: 256px;
          `}
          value={value}
          onChange={onChange}
          options={models.map((i) => ({ label: i.name, value: i.name }))}
        />
      </div>
      <div>
        <Space>
          <Popover trigger="hover" placement="top" content="Clear history">
            <Button
              disabled={!chat || !messages.length || generating}
              type="text"
              icon={<CarbonIcon icon={<Erase />} />}
              onClick={clear}
            />
          </Popover>
          <ApiModal
            disabled={loading || !model}
            icon={<CarbonIcon icon={<Code />} />}
            apiUrl={model?.apiOption.api_url || ""}
            apiKey={model?.apiOption.api_key}
            name={model?.name || ""}
          />
        </Space>
      </div>
    </div>
  );
};
