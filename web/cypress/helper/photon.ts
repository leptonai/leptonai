export const getRandomPhoton = () => {
  return cy
    .exec("node ./cypress/helper/gen-random-photon.cjs --create")
    .then((result) => {
      if (result.code !== 0) {
        throw new Error("Failed to create random photon");
      }
      const output = result.stdout;
      const [name, path] = output.split("\n");
      return { name, path };
    });
};

export const cleanRandomPhoton = () => {
  return cy.exec("node ./cypress/helper/gen-random-photon.cjs --clean");
};

export const removePhotonZip = (name: string) => {
  return cy.exec(
    `node ./cypress/helper/gen-random-photon.cjs --remove ${name}.zip`
  );
};
