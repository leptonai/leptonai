import { alias, intercept } from "../../helper/intercept";

describe("workspace", () => {
  beforeEach(() => {
    intercept();
    cy.visit("http://localhost:3001");

    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);
  });

  describe("dashboard", () => {
    beforeEach(() => {
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

  describe("photons", () => {
    beforeEach(() => {
      cy.get("#nav-photons").click();
      cy.wait(200);
    });

    it("should be render photon list", () => {
      cy.get(".photon-item").should("have.length", 1);
    });
  });

  describe("deployments", () => {
    beforeEach(() => {
      cy.get("#nav-deployments").click();
      cy.wait(200);
    });

    it("should be render deployment list", () => {
      cy.get("#deployment-list li").should("have.length", 1);
    });

    it("should be render deployment detail", () => {
      cy.get("#deployment-list li a:first()").click();
      cy.wait(200);

      cy.get("#api-form").should("have.length", 1);

      cy.get("form label.ant-checkbox-wrapper")
        .contains("Show advanced options")
        .click();

      cy.wait(200);

      cy.percySnapshot("Deployment API Form", {
        scope: "#api-form",
        minHeight: 1800,
      });
    });
  });
});
