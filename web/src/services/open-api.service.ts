import { Injectable } from "injection-js";
import { SafeAny } from "@lepton-dashboard/interfaces/safe-any";
import { sampleFromSchema } from "@lepton-libs/open-api-tool/samples";

@Injectable()
export class OpenApiService {
  sampleFromSchema(schema: SafeAny, override: SafeAny) {
    try {
      return sampleFromSchema(schema, {}, override);
    } catch (e) {
      console.error(e);
      return {};
    }
  }

  /**
   * From https://github.com/swagger-api/swagger-js/blob/master/src/execute/index.js#LL53C17-L53C24
   * Input request object, output response object.
   */
  executeRequest(_request: SafeAny) {
    // TODO
  }

  /**
   * From https://github.com/swagger-api/swagger-js/blob/63cced01d4d8d1e47ccd19010ef972fd6dc2bfad/src/execute/index.js#L249
   * Input Swagger, OpenAPI 2-3 and operationId, output request object.
   */
  buildRequest(_schema: SafeAny, _operationId: string, _body?: SafeAny) {
    // TODO
  }

  /**
   * From https://github.com/swagger-api/swagger-ui/blob/021a1d495c84ee79c4792a92c93d73aee9c4a9c2/src/core/plugins/request-snippets/fn.js#L153
   * Input request object, output curl string.
   */
  curlify(_request: SafeAny) {
    // TODO
  }
}
