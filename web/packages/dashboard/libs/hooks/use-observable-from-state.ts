import { map, Observable } from "rxjs";
import { useObservable } from "observable-hooks";

export const useObservableFromState = <T>(state: T): Observable<T> => {
  return useObservable((d) => d.pipe(map(([e]) => e)), [state]);
};
