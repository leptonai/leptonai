import { HttpContextToken } from "@lepton-dashboard/services/http-client.service";

export interface InterceptorContext {
  ignoreErrors: boolean | number[];
}

/**
 * circular dependency between {@link AppInterceptor} and {@link ProfileService}
 */
export const INTERCEPTOR_CONTEXT = new HttpContextToken<InterceptorContext>(
  () => {
    return {
      ignoreErrors: false,
    };
  }
);
