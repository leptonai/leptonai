export const removeDeployment = (name: string) => {
  cy.request({
    method: "DELETE",
    url: `http://localhost:3001/api/v1/deployments/${name}`,
    headers: {
      Authorization: `Bearer ${Cypress.env("token")}`,
    },
  });
};

export const cleanDeployments = () => {
  cy.request({
    method: "GET",
    url: "http://localhost:3001/api/v1/deployments",
    headers: {
      Authorization: `Bearer ${Cypress.env("token")}`,
    },
  }).then((response) => {
    return Promise.all(
      response.body
        .map((e) => e.name)
        .map((name) => {
          return cy.request({
            method: "DELETE",
            url: `http://localhost:3001/api/v1/deployments/${name}`,
            headers: {
              Authorization: `Bearer ${Cypress.env("token")}`,
            },
          });
        })
    );
  });
};

export const removePhoton = (name: string) => {
  cy.request({
    method: "GET",
    url: "http://localhost:3001/api/v1/photons",
    headers: {
      Authorization: `Bearer ${Cypress.env("token")}`,
    },
  }).then((response) => {
    return Promise.all(
      response.body
        .map((e) => e.id)
        .filter((e) => e.startsWith(name))
        .map((name) => {
          return cy.request({
            method: "DELETE",
            url: `http://localhost:3001/api/v1/photons/${name}`,
            headers: {
              Authorization: `Bearer ${Cypress.env("token")}`,
            },
          });
        })
    );
  });
};

export const uploadPhoton = (base64File: string) => {
  const blob = Cypress.Blob.base64StringToBlob(base64File);
  const formData = new FormData();
  formData.append("file", blob);
  cy.request({
    method: "POST",
    url: "http://localhost:3001/api/v1/photons",
    headers: {
      Authorization: `Bearer ${Cypress.env("token")}`,
    },
    body: formData,
  });
};

export const cleanPhotons = () => {
  cy.request({
    method: "GET",
    url: "http://localhost:3001/api/v1/photons",
    headers: {
      Authorization: `Bearer ${Cypress.env("token")}`,
    },
  }).then((response) => {
    return Promise.all(
      response.body
        .map((e) => e.id)
        .filter((e) => e.startsWith("e2e-test"))
        .map((name) => {
          return cy.request({
            method: "DELETE",
            url: `http://localhost:3001/api/v1/photons/${name}`,
            headers: {
              Authorization: `Bearer ${Cypress.env("token")}`,
            },
          });
        })
    );
  });
};

export const cleanPhotonsBefore = (time: number) => {
  cy.request({
    method: "GET",
    url: "http://localhost:3001/api/v1/photons",
    headers: {
      Authorization: `Bearer ${Cypress.env("token")}`,
    },
  }).then((response) => {
    return Promise.all(
      response.body
        .filter((e) => e.created_at + time < Date.now())
        .map((e) => e.id)
        .filter((e) => e.startsWith("e2e-test"))
        .map((name) => {
          return cy.request({
            method: "DELETE",
            url: `http://localhost:3001/api/v1/photons/${name}`,
            headers: {
              Authorization: `Bearer ${Cypress.env("token")}`,
            },
          });
        })
    );
  });
};
