import { ChatBot, MagicWandFilled } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ScrollableRef } from "@lepton-dashboard/components/scrollable";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Container } from "@lepton-dashboard/routers/playground/components/container";
import { PlaygroundService } from "@lepton-dashboard/routers/playground/service/playground.service";
import { useInject } from "@lepton-libs/di";
import { ChatOptions } from "@lepton-libs/gradio/chat-options";
import {
  ChatCompletion,
  ChatOption,
  ChatService,
} from "@lepton-libs/gradio/chat.service";
import { PromptInput, PromptInputRef } from "@lepton-libs/gradio/prompt-input";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import pathJoin from "@lepton-libs/url/path-join";
import { FC, useCallback, useMemo, useRef, useState } from "react";
import {
  combineLatest,
  filter,
  map,
  Subscription,
  switchMap,
  tap,
  throttleTime,
} from "rxjs";
import { MetaService } from "@lepton-dashboard/services/meta.service";
import { Dropdown, Space } from "antd";
import { DownOutlined } from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import { MDMessage } from "@lepton-dashboard/routers/playground/routers/code-llama/components/md-message";
import { PresetSelector } from "@lepton-dashboard/routers/playground/components/preset-selector";
import { Api } from "@lepton-dashboard/routers/playground/components/api";
import { APICodeTemplates } from "@lepton-libs/gradio/code-api-modal";

const presets = [
  {
    name: "Fibonacci",
    prompt: "# Python\n" + "def fibonacci(n):",
  },
  {
    name: "SQL",
    prompt: "Create a user table using SQL and randomly insert 3 records\n",
  },
  {
    name: "JSON to YAML",
    prompt:
      "Convert the following JSON to YAM\n" +
      "\n" +
      "```json\n" +
      "{\n" +
      '  "by" : "norvig",\n' +
      '  "id" : 2921983,\n' +
      '  "kids" : [ 2922097, 2922429, 2924562, 2922709, 2922573, 2922140, 2922141 ],\n' +
      '  "parent" : 2921506,\n' +
      '  "text" : "Aw shucks, guys ... you make me blush with your compliments.<p>Tell you what, Ill make a deal: I\'ll keep writing if you keep reading. K?",\n' +
      '  "time" : 1314211127,\n' +
      '  "type" : "comment"\n' +
      "}\n" +
      "```\n",
  },
  {
    name: "Refactor code",
    prompt:
      "Refactor the following code using Python\n" +
      "\n" +
      "```c\n" +
      "class Main {\n" +
      "public:\n" +
      "    int lengthOfLongestSubstring(string s) {\n" +
      "        int start = 0;\n" +
      "        int end = 0;\n" +
      "        int max = 0;\n" +
      "        for (int i = 0; i < s.size(); ++i) {\n" +
      "            for (end = start; end < i; ++ end) {\n" +
      "                if (s[end] == s[i]) {\n" +
      "                    start = end + 1;\n" +
      "                    break;\n" +
      "                }\n" +
      "            }\n" +
      "            if (end - start + 1 > max) {\n" +
      "                max = end - start + 1;\n" +
      "            }\n" +
      "        }\n" +
      "        return max;\n" +
      "    }\n" +
      "};\n" +
      "```\n",
  },
  {
    name: "Explain code",
    prompt:
      "Explain the following code \n" +
      "\n" +
      "```\n" +
      "data:text/html,<html contenteditable>\n" +
      "```\n",
  },
];

const presetOptions = presets.map((p) => ({
  label: p.name,
  value: p.prompt,
  placeholder: "Load a preset",
}));

export const CodeLlama: FC = () => {
  const metaService = useInject(MetaService);
  metaService.setTitle("💻 🦙 Code Llama", true);
  metaService.setURLPath();
  const inputRef = useRef<PromptInputRef>(null);
  const [params] = useSearchParams();
  const modelFromURL = params.get("model") || "";
  const [model, setModel] = useState<string>(modelFromURL);
  const [url, setUrl] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [option, setOption] = useState<ChatOption>({
    max_tokens: 256,
    top_p: 0.9,
    temperature: 0.1,
  });
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("# Python\n" + "def fibonacci(n):");
  const subscriptionRef = useRef<Subscription>(Subscription.EMPTY);
  const chatService = useInject(ChatService);
  const theme = useAntdTheme();
  const playgroundService = useInject(PlaygroundService);
  const chat = useStateFromObservable(
    () =>
      combineLatest([
        playgroundService.getCodeLlamaBackend(),
        playgroundService.listCodeLlamaModels(),
      ]).pipe(
        tap(([url, models]) => {
          setModels(models);
          setUrl(url);
          const normalModel =
            models.find((item) => item === modelFromURL) || models[0];
          setModel(normalModel);
          setOption((pre) => {
            return {
              ...pre,
              model: normalModel,
            };
          });
          setLoading(false);
        }),
        map(([url]) =>
          chatService.createChat({
            api_url: pathJoin(url, "chat/completions"),
          })
        )
      ),
    null
  );
  const chat$ = useObservableFromState(chat);
  const scrollRef = useRef<ScrollableRef>(null);
  const submit = useCallback(() => {
    if (submitting || !prompt || !chat) {
      return;
    }
    chat.clear();
    subscriptionRef.current = chat
      .send(prompt, option)
      .pipe(throttleTime(100))
      .subscribe(() => scrollRef?.current?.scrollToBottom());
  }, [submitting, prompt, chat, option]);

  const message = useStateFromObservable(
    () =>
      chat$.pipe(
        filter((instance): instance is ChatCompletion => !!instance),
        switchMap((instance) => instance.onMessagesChanged()),
        map((messages) => {
          const item = messages.find((m) => m.message.role === "assistant");
          return item ? Object.assign({}, item) : null;
        })
      ),
    null,
    {
      next: (value) => {
        const loading = value?.loading || false;
        setSubmitting(loading);
      },
      error: () => {
        setSubmitting(false);
      },
    }
  );

  const presetPrompt = useMemo(() => {
    if (presets.some((p) => p.prompt === prompt)) {
      return prompt;
    } else {
      return undefined;
    }
  }, [prompt]);

  const modelMenu = useMemo(() => {
    return {
      items: models.map((key) => ({
        key,
        label: key,
        title: key,
      })),
      onClick: ({ key }: { key: string }) => {
        setModel(key);
        setOption((pre) => {
          return {
            ...pre,
            model: key,
          };
        });
        // focus input
        inputRef.current?.focus();
        // set query params
        const url = new URL(window.location.href);
        url.searchParams.set("model", key);
        window.history.replaceState({}, "", url.toString());
      },
    };
  }, [models]);

  return (
    <Container
      loading={!chat}
      icon={<CarbonIcon icon={<ChatBot />} />}
      title={
        modelMenu.items.length > 0 ? (
          <>
            <Dropdown menu={modelMenu} trigger={["click"]}>
              <Space
                css={css`
                  cursor: pointer;
                `}
              >
                <span
                  css={css`
                    @media (max-width: 480px) {
                      max-width: 80px;
                      display: inline-block;
                      overflow: hidden;
                      line-height: 10px;
                      text-overflow: ellipsis;
                    }
                  `}
                >
                  {model}
                </span>
                <DownOutlined />
              </Space>
            </Dropdown>
          </>
        ) : (
          <span>{loading ? "Loading models..." : "No model available"}</span>
        )
      }
      extra={
        <Space>
          <PresetSelector
            options={presetOptions}
            value={presetPrompt}
            onChange={(v) => {
              setPrompt(v);
            }}
          />
          <Api
            name="Code Llama"
            code={APICodeTemplates.chat(
              url,
              '"<YOUR_EMAIL_ADDRESS>" # for using API from playground, you may use your email address here',
              "# Python\\n" + "def fibonacci(n):"
            )}
          />
        </Space>
      }
      content={
        <div
          css={css`
            flex: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            position: relative;
          `}
        >
          <PromptInput
            css={css`
              flex: 0 1 auto;
            `}
            submitIcon={<CarbonIcon icon={<MagicWandFilled />} />}
            submitText="Generate"
            ref={inputRef}
            maxRows={8}
            loading={submitting}
            value={prompt}
            onChange={setPrompt}
            onSubmit={submit}
            onCancel={() => subscriptionRef.current.unsubscribe()}
          />
          <div
            css={css`
              border: 1px solid ${theme.colorBorder};
              flex: 1 1 auto;
              min-height: 300px;
              overflow: hidden;
              position: relative;
              display: flex;
              margin-top: 12px;
              border-radius: ${theme.borderRadius}px;
            `}
          >
            <div
              css={css`
                position: absolute;
                inset: 0;
                display: flex;
                flex-direction: column;
              `}
            >
              <MDMessage
                content={message?.message.content}
                error={message?.error}
                loading={message?.loading}
                responseTime={message?.responseTime}
                completionTime={message?.completionTime}
                ref={scrollRef}
              />
            </div>
          </div>
        </div>
      }
      option={
        <ChatOptions chatOption={option} onChatOptionChanged={setOption} />
      }
    />
  );
};
