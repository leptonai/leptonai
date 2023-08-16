export enum alias {
  getWorkspace = "getWorkspace",
  getDeployments = "getDeployments",
  getPhotons = "getPhotons",
  deletePhoton = "deletePhoton",
  getFastAPIQPS = "getFastAPIQPS",
  getFastAPIQPSByPath = "getFastAPIQPSByPath",
  getFastAPILatency = "getFastAPILatency",
  getFastAPILatencyByPath = "getFastAPILatencyByPath",
  getImagePullSecrets = "getImagePullSecrets",
  getSecrets = "getSecrets",
}

export const intercept = () => {
  // intercept the workspace request
  cy.intercept("GET", "/api/v1/workspace").as(alias.getWorkspace);

  // intercept the deployments request
  cy.intercept("GET", "/api/v1/deployments").as(alias.getDeployments);

  // intercept the photons request
  cy.intercept("GET", "/api/v1/photons").as(alias.getPhotons);
  cy.intercept("DELETE", "/api/v1/photons/*").as(alias.deletePhoton);

  // intercept the deployments/[id]/monitoring/FastAPIQPS request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPIQPS").as(
    alias.getFastAPIQPS
  );

  // intercept the deployments/[id]/monitoring/FastAPIQPSByPath request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPIQPSByPath").as(
    alias.getFastAPIQPSByPath
  );

  // intercept the deployments/[id]/monitoring/FastAPILatency request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPILatency").as(
    alias.getFastAPILatency
  );

  // intercept the deployments/[id]/monitoring/FastAPILatencyByPath request
  cy.intercept(
    "GET",
    "api/v1/deployments/*/monitoring/FastAPILatencyByPath"
  ).as(alias.getFastAPILatencyByPath);

  // intercept the imagePullSecrets request
  cy.intercept("GET", "/api/v1/imagepullsecrets").as(alias.getImagePullSecrets);

  // intercept the secrets request
  cy.intercept("GET", "/api/v1/secrets").as(alias.getSecrets);
};
