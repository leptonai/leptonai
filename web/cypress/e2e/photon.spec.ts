import { alias, intercept } from "../helper/intercept";

describe("photons", () => {
  beforeEach(() => {
    intercept();
    cy.visit("http://localhost:3001");

    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);

    cy.get("#nav-photons").click();
    cy.wait(200);
  });

  it("should be render photon list", () => {
    cy.get(".photon-item").should("have.length", 1);
  });
});
