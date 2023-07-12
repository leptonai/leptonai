export enum alias {
  getWorkspace = "getWorkspace",
  getDeployments = "getDeployments",
  getPhotons = "getPhotons",
  getFastAPIQPS = "getFastAPIQPS",
  getFastAPIQPSByPath = "getFastAPIQPSByPath",
  getFastAPILatency = "getFastAPILatency",
  getFastAPILatencyByPath = "getFastAPILatencyByPath",
}

export const intercept = () => {
  // intercept the workspace request
  cy.intercept("GET", "/api/v1/workspace", {
    fixture: "api/v1/workspace.json",
  }).as(alias.getWorkspace);

  // intercept the deployments request
  cy.intercept("GET", "/api/v1/deployments", {
    fixture: "api/v1/deployments.json",
  }).as(alias.getDeployments);

  // intercept the photons request
  cy.intercept("GET", "/api/v1/photons", {
    fixture: "api/v1/photons.json",
  }).as(alias.getPhotons);

  // intercept the deployments/[id]/monitoring/FastAPIQPS request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPIQPS", {
    fixture: "api/v1/deployments/[id]/monitoring/FastAPIQPS.json",
  }).as(alias.getFastAPIQPS);

  // intercept the deployments/[id]/monitoring/FastAPIQPSByPath request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPIQPSByPath", {
    fixture: "api/v1/deployments/[id]/monitoring/FastAPIQPSByPath.json",
  }).as(alias.getFastAPIQPSByPath);

  // intercept the deployments/[id]/monitoring/FastAPILatency request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPILatency", {
    fixture: "api/v1/deployments/[id]/monitoring/FastAPILatency.json",
  }).as(alias.getFastAPILatency);

  // intercept the deployments/[id]/monitoring/FastAPILatencyByPath request
  cy.intercept("GET", "api/v1/deployments/*/monitoring/FastAPILatencyByPath", {
    fixture: "api/v1/deployments/[id]/monitoring/FastAPILatencyByPath.json",
  }).as(alias.getFastAPILatencyByPath);
};
