describe("app", () => {
  beforeEach(() => {
    // intercept the cluster request
    cy.intercept("GET", "/api/v1/cluster", {
      fixture: "api/v1/cluster.json",
    }).as("getCluster");

    // intercept the deployments request
    cy.intercept("GET", "/api/v1/deployments", {
      fixture: "api/v1/deployments.json",
    }).as("getDeployments");

    // intercept the photons request
    cy.intercept("GET", "/api/v1/photons", {
      fixture: "api/v1/photons.json",
    }).as("getPhotons");

    cy.visit("http://localhost:3001");
  });

  it("should be redirected to workspace dashboard", () => {
    cy.wait("@getCluster");
    cy.url({ timeout: 100 }).should("match", /.+\/workspace/);

    cy.wait("@getDeployments");
    cy.wait("@getPhotons");

    cy.url({ timeout: 100 }).should("match", /.+\/workspace\/.+\/dashboard/);

    cy.percySnapshot();
  });
});
