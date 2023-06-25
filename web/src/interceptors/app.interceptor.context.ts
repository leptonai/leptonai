import { HttpContextToken } from "@lepton-dashboard/services/http-client.service";

/**
 * circular dependency between {@link AppInterceptor} and {@link ProfileService}
 */
export const INTERCEPTOR_CONTEXT = new HttpContextToken(() => {
  return {
    ignoreErrors: false,
  };
});
