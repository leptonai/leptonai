import { alias, intercept } from "../helper/intercept";
import { saveToken } from "../helper/save-token";
describe("dashboard", () => {
  beforeEach(() => {
    saveToken();
    intercept();
    cy.visit("http://localhost:3001");

    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);
  });

  it("should be redirect to dashboard", () => {
    cy.url().should("include", "/dashboard");
  });

  it("should be render getting-started", () => {
    cy.get("h3").contains("Getting Started").should("be.exist");
  });
});
