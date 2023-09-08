import { retry, timer } from "rxjs";
import { UnauthorizedError } from "@lepton-libs/erroes/unauthorized";

export const retryBackoff = <T>(options: { count: number; delay: number }) => {
  return retry<T>({
    count: options.count,
    delay: (error, retryCount) => {
      if (error instanceof UnauthorizedError) {
        throw error;
      }
      const delay = Math.pow(1.2, retryCount - 1) * options.delay;
      return timer(delay);
    },
  });
};
