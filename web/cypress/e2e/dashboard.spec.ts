import { alias, intercept } from "../helper/intercept";
describe("dashboard", () => {
  beforeEach(() => {
    intercept();
    cy.visit("http://localhost:3001");

    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);
    cy.get("#nav-dashboard").click();
    cy.wait(200);
  });

  it("should be render dashboard", () => {
    cy.get(".total-photons .ant-statistic-content-value").should(
      "have.text",
      "1"
    );

    cy.get(".total-deployments .ant-statistic-content-value").should(
      "have.text",
      "1"
    );
  });
});
