import { alias, intercept } from "../helper/intercept";

describe("deployments", () => {
  beforeEach(() => {
    intercept();
    cy.visit("http://localhost:3001");

    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);

    cy.get("#nav-deployments").click();
    cy.wait(200);
  });

  it("should be render deployment list", () => {
    cy.get("#deployment-list li").should("have.length", 1);
  });

  it("should be edit deployment current", () => {
    cy.get("#deployment-list li button").contains("Edit").click();
    cy.wait(300); // modal animation
    cy.wait(`@${alias.getImagePullSecrets}`);
    cy.get("input#min_replicas").as("replicasInput");
    cy.get("@replicasInput").should("have.value", "1");
    cy.contains("Advanced settings").click();
    cy.wait(300); //collapse animation
    cy.get(".ant-collapse").contains("HUGGING_FACE_HUB_TOKEN").should("exist");
    cy.get(".ant-collapse input[value='/hsuanxyz']").should("exist");
    cy.get(".ant-collapse input[value='/user']").should("exist");
    cy.get(".ant-collapse").contains("registry-1").should("exist");

    cy.intercept("PATCH", "/api/v1/deployments/*", (req) => {
      expect(req.body?.resource_requirement?.min_replicas).to.eq(2);
      expect(req.body?.api_tokens).to.be.undefined;
      expect(req.body?.envs).to.be.undefined;
      expect(req.body?.mounts).to.be.undefined;
      expect(req.body?.image_pull_secrets).to.be.undefined;
      expect(req.body?.status).to.be.undefined;

      req.reply({
        statusCode: 200,
        body: null,
      });
    });

    cy.get("@replicasInput").clear().type("2");
    cy.get("button").contains("Save").click();

    cy.wait(300); // modal animation
    cy.get(".ant-modal-title").should("not.exist");
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
