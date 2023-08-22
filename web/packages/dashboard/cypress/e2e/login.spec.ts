import { intercept } from "../helper/intercept";
import { saveToken } from "../helper/save-token";
describe("login with token", () => {
  beforeEach(() => {
    intercept();
    cy.visit("http://localhost:3001");
    cy.wait(1000);
  });

  it("should be render login page", () => {
    cy.url().should("include", "/login");
  });

  it("should be login success", () => {
    cy.get("input[type=password]").type(Cypress.env("token"));
    cy.get("button[type=submit]").click();
    cy.url().should("include", "/dashboard");
  });
});

describe("logout with token", () => {
  beforeEach(() => {
    saveToken();
    cy.visit("http://localhost:3001");
    cy.wait(1000);
  });

  it("should be logout success", () => {
    cy.getAllLocalStorage().then((object) => {
      cy.wrap(object["http://localhost:3001"]).should(
        "have.property",
        "lepton-global-lepton-workspace-token"
      );
    });
    cy.contains("yourself@lepton.ai").trigger("mouseover");
    cy.wait(200);
    cy.contains("Logout").click();
    cy.url().should("include", "/login");
    cy.getAllLocalStorage().then((object) => {
      cy.wrap(
        object["http://localhost:3001"]["lepton-global-lepton-workspace-token"]
      ).should("eq", "");
    });
  });
});
