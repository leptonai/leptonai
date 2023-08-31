import { alias, intercept } from "../helper/intercept";
import { saveToken } from "../helper/save-token";
import { removePhoton, uploadPhoton } from "../helper/request";
import { getRandomPhoton, removePhotonZip } from "../helper/photon";

describe("deployments", () => {
  let photonName: string;
  const deploymentName = `e2e-test-${Date.now()}`;
  before(() => {
    getRandomPhoton().then((photon) => {
      photonName = photon.name;

      cy.fixture(photon.path.replace("cypress/fixtures/", "")).then(
        (fileContent) => {
          uploadPhoton(fileContent);
        }
      );
    });
  });

  after(() => {
    removePhoton(photonName);
    cy.wait(2000);
    removePhotonZip(photonName);
  });

  beforeEach(() => {
    saveToken();
    intercept();
    cy.visit("http://localhost:3001");

    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);

    cy.get("#nav-deployments").click();
    cy.wait(200);
  });

  it("should be navigate to deployments", () => {
    cy.url().should("include", "/deployments/list");
  });

  it("should be create a deployment with photon", () => {
    cy.get("button").contains("Create deployment").click();
    cy.wait(200);
    cy.get(".ant-modal-content").should("be.exist");
    cy.get(".ant-modal-content input").first().type(deploymentName);
    cy.get(".ant-modal-content button").contains("Create").click();
    cy.wait(1000);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(`@${alias.getDeployments}`);
    cy.get(".deployment-item")
      .contains(deploymentName)
      .parentsUntil(".deployment-item")
      .should("be.exist");
  });

  it("should be edit deployment current", () => {
    cy.get(".deployment-item")
      .contains(deploymentName)
      .parentsUntil(".deployment-item")
      .get("button")
      .contains("Edit")
      .click();
    cy.wait(300); // modal animation
    cy.wait(`@${alias.getImagePullSecrets}`);
    cy.get("input#min_replicas").as("replicasInput");
    cy.get("@replicasInput").should("have.value", "1");

    cy.intercept("PATCH", "/api/v1/deployments/*", (req) => {
      expect(req.body?.resource_requirement?.min_replicas).to.eq(2);
      expect(req.body?.api_tokens).to.be.deep.eq([
        {
          value_from: {
            token_name_ref: "WORKSPACE_TOKEN",
          },
        },
      ]);
      expect(req.body?.envs).to.be.undefined;
      expect(req.body?.mounts).to.be.undefined;
      expect(req.body?.image_pull_secrets).to.be.undefined;
      expect(req.body?.status).to.be.undefined;
    });

    cy.get("@replicasInput").clear().type("2");
    cy.get("button").contains("Save").click();

    cy.wait(300); // modal animation
    cy.get(".ant-modal-title").should("not.exist");
    cy.wait(`@${alias.getDeployments}`);
    cy.get(".deployment-item")
      .contains(deploymentName)
      .parentsUntil(".deployment-item")
      .contains("2 replicas");
  });

  describe("deployment detail", () => {
    beforeEach(() => {
      cy.get(".deployment-item").contains(deploymentName).click();
      cy.wait(200);
    });

    it("should be navigate to deployment detail", () => {
      cy.url().should("include", "/deployments/detail");
    });

    it("should be render deployment detail", () => {
      cy.get("#api-form").should("be.exist");

      cy.percySnapshot("api-form", {
        scope: "#api-form",
      });
    });

    it("should be delete deployment", () => {
      cy.intercept("DELETE", "/api/v1/deployments/*", (req) => {
        expect(req.body).to.be.empty;
      }).as("deleteDeployment");
      cy.get("button").contains("Delete").click();
      cy.wait(200);
      cy.get(".ant-popover-content button").contains("OK").click();
      cy.wait(`@deleteDeployment`);
      cy.wait(1000);
      cy.url().should("include", "/deployments/list");
      cy.wait(`@${alias.getDeployments}`);
      cy.contains(deploymentName).should("not.exist");
    });
  });
});
