export const saveToken = () => {
  cy.window().then((win) => {
    win.localStorage.setItem(
      "lepton-global-lepton-workspace-token",
      Cypress.env("token")
    );
  });
};
