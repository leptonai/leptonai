import { HttpContextToken } from "@lepton-dashboard/services/http-client.service";

export interface InterceptorContext {
  /**
   * @note 401 needs to be ignored explicitly
   */
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
