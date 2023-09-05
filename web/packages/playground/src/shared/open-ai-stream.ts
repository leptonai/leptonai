import {
  createParser,
  ParsedEvent,
  ReconnectInterval,
} from "eventsource-parser";
import { Observable, throwError } from "rxjs";

export type ChatGPTAgent = "user" | "system" | "assistant";

export interface ChatGPTMessage {
  role: ChatGPTAgent;
  content: string;
}

export interface OpenAIStreamOption {
  api_url: string;
  api_key?: string;
  api_org?: string;
}

export interface OpenAIStreamPayload {
  model: string;
  stream: true;
  messages: ChatGPTMessage[];
  temperature?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  max_tokens?: number;
  stop?: string[];
  user?: string;
  n?: number;
}

const defaultOption: OpenAIStreamOption = {
  api_url: "/v1/chat/completions",
  api_key: "",
  api_org: "",
} as const;

const asyncIterable = {
  async *[Symbol.asyncIterator](stream: ReadableStream<Uint8Array> | null) {
    if (!stream) {
      return;
    }
    const reader = stream.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          return;
        }
        yield value;
      }
    } finally {
      reader.releaseLock();
    }
  },
};

export async function openAIStream(
  payload: OpenAIStreamPayload,
  option: Partial<OpenAIStreamOption> = {},
  abortController: AbortController = new AbortController()
) {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  // eslint-disable-next-line no-param-reassign
  option = { ...defaultOption, ...option };
  option.api_url = option.api_url || defaultOption.api_url;
  let counter = 0;

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (option.api_key) {
    requestHeaders.Authorization = `Bearer ${option.api_key ?? ""}`;
  }

  if (option.api_org) {
    requestHeaders["OpenAI-Organization"] = option.api_org;
  }

  const res = await fetch(option.api_url, {
    headers: requestHeaders,
    method: "POST",
    body: JSON.stringify(payload),
    signal: abortController.signal,
  });

  if (!res.ok) {
    const json = await res.json();
    return throwError(json);
  }

  const stream = new ReadableStream({
    async start(controller) {
      // callback
      function onParse(event: ParsedEvent | ReconnectInterval) {
        if (event.type === "event") {
          const { data } = event;
          // https://beta.openai.com/docs/api-reference/completions/create#completions/create-stream
          if (data === "[DONE]") {
            controller.close();
            return;
          }
          try {
            const json = JSON.parse(data);
            const text = json.choices[0].delta?.content || "";
            if (counter < 2 && (text.match(/\n/) || []).length) {
              // this is a prefix character (i.e., "\n\n"), do nothing
              return;
            }
            const queue = encoder.encode(text);
            controller.enqueue(queue);
            counter += 1;
          } catch (e) {
            // maybe parse error
            controller.error(e);
          }
        }
      }
      // stream response (SSE) from OpenAI may be fragmented into multiple chunks
      // this ensures we properly read chunks and invoke an event for each SSE event stream
      const parser = createParser(onParse);

      for await (const chunk of asyncIterable[Symbol.asyncIterator](res.body)) {
        parser.feed(decoder.decode(chunk));
      }
    },
  });

  return new Observable<string>((subscriber) => {
    stream.pipeTo(
      new WritableStream({
        write: (chunk) => {
          subscriber.next(decoder.decode(chunk));
        },
        abort: (error) => {
          subscriber.error(error);
        },
        close: () => {
          subscriber.complete();
        },
      })
    );
    return () => {
      abortController.abort();
      if (!stream.locked) {
        stream.cancel();
      }
    };
  });
}
