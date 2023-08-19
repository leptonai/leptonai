import { alias, intercept } from "../helper/intercept";
import { saveToken } from "../helper/save-token";
import { getRandomPhoton, removePhotonZip } from "../helper/photon";
import { removeDeployment, removePhoton } from "../helper/request";

describe("photons", () => {
  let photonName: string;
  let photonPath: string;
  const deploymentName = `e2e-test-${Date.now()}`;
  before(() => {
    getRandomPhoton().then((photon) => {
      photonName = photon.name;
      photonPath = photon.path;
    });
  });

  after(() => {
    removePhoton(photonName);
    removePhotonZip(photonName);
  });

  beforeEach(() => {
    saveToken();
    intercept();
    cy.visit("http://localhost:3001");
    cy.wait(`@${alias.getDeployments}`);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(1000);

    cy.get("#nav-photons").click();
    cy.wait(200);
  });

  it("should be navigate to photons", () => {
    cy.url().should("include", "/photons/list");
  });

  it("should be upload photon", () => {
    cy.get("button").contains("Upload photon").click();
    cy.get(".ant-upload input[type=file]").selectFile(photonPath, {
      force: true,
    });
    cy.wait(`@${alias.getPhotons}`);
    cy.get(".photon-item").contains(photonName).should("be.exist");
  });

  it("should be create a deployment in photon card", () => {
    const photon = cy
      .get(".photon-item")
      .contains(photonName)
      .parentsUntil(".photon-item");
    photon.contains("No deployment").should("be.exist");
    photon.get("button").contains("Deploy").click();
    cy.wait(200);
    cy.get(".ant-modal-content").should("be.exist");
    cy.get(".ant-modal-content input").first().type(deploymentName);
    cy.get(".ant-modal-content button").contains("Create").click();
    cy.wait(1000);
    cy.wait(`@${alias.getPhotons}`);
    cy.wait(`@${alias.getDeployments}`);
    cy.get(".photon-item")
      .contains(photonName)
      .parentsUntil(".photon-item")
      .contains("1 deployment")
      .should("be.exist");
  });

  it("should disable deletion of photon when it has deployment", () => {
    cy.get("a").contains(photonName).click();
    cy.url().should("include", "/photons/version");
    cy.get("button").contains("Delete").parent("button").should("be.disabled");
  });

  it("should be delete photon", () => {
    removeDeployment(deploymentName);
    cy.get("a").contains(photonName).click();
    cy.get("button").contains("Delete").click();
    cy.get(".ant-popover-content button").contains("OK").click();
    cy.wait(`@${alias.deletePhoton}`);
    cy.wait(200);
    cy.url().should("include", "/photons/list");
    cy.contains(photonName).should("not.exist");
  });
});
