import { Observable, PartialObserver } from "rxjs";
import { useObservableEagerState, useSubscription } from "observable-hooks";
import { useState } from "react";
import { useOnce } from "@lepton-libs/hooks/use-once.ts";

export const useStateFromObservable = <T>(
  factory: () => Observable<T>,
  initialState: T,
  observer?: PartialObserver<T>
): T => {
  const observable$ = useOnce(() => factory());
  const [state, setState] = useState<T>(initialState);
  useSubscription(observable$, {
    next: (v) => {
      setState(v);
      observer && observer.next && observer.next(v);
    },
    complete: () => observer && observer.complete && observer.complete(),
    error: (v) => observer && observer.error && observer.error(v),
  });
  return state;
};

export const useStateFromBehaviorSubject = <T>(input$: Observable<T>): T => {
  return useObservableEagerState(input$);
};
