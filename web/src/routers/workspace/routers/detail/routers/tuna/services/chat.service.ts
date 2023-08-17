import { Injectable } from "injection-js";
import {
  ChatGPTMessage,
  openAIStream,
  OpenAIStreamOption,
} from "@lepton-libs/open-ai-like/open-ai-stream";
import { BehaviorSubject, Observable } from "rxjs";

export interface ChatMessageItem {
  loading?: boolean;
  error?: string;
  responseTime?: number;
  completionTime?: number;
  message: ChatGPTMessage;
}

export interface ModelOption {
  name: string;
  apiOption: OpenAIStreamOption;
}

export const benchmarkModel: ModelOption = {
  name: "llama2",
  apiOption: {
    api_url: "https://llama2.llm.lepton.run/api/v1",
  },
} as const;

export interface ChatOption {
  temperature: number;
  top_p: number;
  max_tokens: number;
}
export interface ChatCompletion {
  onGeneratingChanged(): Observable<boolean>;
  onMessagesChanged(): Observable<ChatMessageItem[]>;
  send(content: string, option: ChatOption): Observable<string>;
  clear(): void;
}

class Chat implements ChatCompletion {
  private messages$ = new BehaviorSubject<ChatMessageItem[]>([]);
  private generating$ = new BehaviorSubject<boolean>(false);

  constructor(private option: OpenAIStreamOption) {}

  onGeneratingChanged(): Observable<boolean> {
    return this.generating$.asObservable();
  }

  onMessagesChanged(): Observable<ChatMessageItem[]> {
    return this.messages$.asObservable();
  }

  send(content: string, option: ChatOption): Observable<string> {
    this.generating$.next(true);
    const userItem: ChatMessageItem = {
      message: {
        role: "user",
        content,
      },
      loading: false,
    };
    this.push(userItem);

    const messages = this.messages$.value
      .filter((item) => !item.loading && !item.error)
      .map((item) => item.message);

    const aiItem = this.pushLoading();

    return new Observable((subscriber) => {
      const abortController = new AbortController();
      const now = Date.now();
      openAIStream(
        {
          model: "gpt-3.5-turbo",
          messages,
          stream: true,
          temperature: option.temperature,
          top_p: option.top_p,
          max_tokens: option.max_tokens,
        },
        this.option,
        abortController
      )
        .then((stream$) => {
          aiItem.responseTime = Date.now() - now;
          this.refresh();
          stream$.subscribe({
            next: (chunkOfMessages) => {
              aiItem.message.content += chunkOfMessages;
              subscriber.next(chunkOfMessages);
              this.refresh();
            },
            complete: () => {
              aiItem.completionTime = Date.now() - now;
              this.refresh();
              aiItem.loading = false;
              subscriber.next("[DONE]");
              subscriber.complete();
              this.generating$.next(false);
            },
            error: (e) => {
              aiItem.completionTime = Date.now() - now;
              aiItem.loading = false;
              if (abortController.signal.aborted) {
                this.refresh();
                return;
              }
              if (typeof e === "string") {
                aiItem.error = e;
              } else if (e instanceof Error) {
                aiItem.error = e.message;
              } else {
                aiItem.error = e?.error?.message || "Something went wrong";
              }
              this.refresh();
              subscriber.error(e);
              this.generating$.next(false);
            },
          });
        })
        .catch((e) => {
          aiItem.loading = false;
          if (typeof e === "string") {
            aiItem.error = e;
          } else if (e instanceof Error) {
            aiItem.error = e.message;
          } else {
            aiItem.error = "Something went wrong";
          }
          this.refresh();
          subscriber.error(e);
          this.generating$.next(false);
        });
      return () => {
        abortController.abort();
        if (!aiItem.responseTime && !aiItem.error) {
          this.remove(userItem);
          this.remove(aiItem);
        } else {
          aiItem.loading = false;
          this.refresh();
        }
        this.generating$.next(false);
      };
    });
  }

  clear(): void {
    if (this.generating$.value) {
      return;
    }
    this.messages$.next([]);
  }

  private refresh(): void {
    this.messages$.next([...this.messages$.value]);
  }

  private remove(item: ChatMessageItem): void {
    this.messages$.next(this.messages$.value.filter((i) => i !== item));
  }

  private push(item: ChatMessageItem): void {
    this.messages$.next([...this.messages$.value, item]);
  }

  private pushLoading(): ChatMessageItem {
    const item: ChatMessageItem = {
      loading: true,
      message: {
        role: "assistant",
        content: "",
      },
    };
    this.push(item);
    return item;
  }
}

@Injectable()
export class ChatService {
  static isUserMessage = (message: ChatMessageItem): boolean => {
    return message.message.role === "user";
  };

  createChat(option: OpenAIStreamOption): ChatCompletion {
    return new Chat(option);
  }
}
