/**
 * @openapi
 * openapi: "2.0"
 * info:
 *   title: Portal API
 *   version: 1.0.0
 * host: portal.lepton.ai
 * schemes:
 *   - https
 * tags:
 *   - name: Auth
 *     description: Authentication APIs
 *   - name: Billing
 *     description: Billing APIs
 *   - name: Workspace
 *     description: Workspace APIs
 * security:
 *   - user
 *   - admin
 * securityDefinitions:
 *   cookieAuth:
 *     type: apiKey
 *     in: cookie
 *     name: sb-oauth-auth-token
 *   serverAuth:
 *     type: apiKey
 *     in: query
 *     name: LEPTON_API_SECRET
 * definitions:
 *   ResponseError:
 *     type: object
 *     properties:
 *       error:
 *        type: string
 *        description: Error message
 */
