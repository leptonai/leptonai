import { Observable, PartialObserver } from "rxjs";
import {
  useObservableEagerState,
  useObservableState,
  useSubscription,
} from "observable-hooks";
import { useOnce } from "@lepton-libs/hooks/use-once.ts";

export const useStateFromObservable = <T>(
  factory: () => Observable<T>,
  initialState: T,
  observer?: PartialObserver<T>
): T => {
  const input$ = useOnce(() => factory());
  useSubscription(input$, observer);
  return useObservableState(input$, initialState);
};

export const useStateFromBehaviorSubject = <T>(
  input$: Observable<T>,
  observer?: PartialObserver<T>
): T => {
  useSubscription(input$, observer);
  return useObservableEagerState(input$);
};
