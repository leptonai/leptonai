const fs = require("fs-extra");
const archiver = require("archiver");
const path = require("path");

const photonDir = `${__dirname}/../fixtures/photons`;
const tempDir = `${__dirname}/../fixtures/__temp`;

/**
 * Generates a random photon and returns the path to the zipped photon
 * @returns {Promise<void>}
 */
const genRandomPhoton = async () => {

  const name = `e2e-test-shell-${(Math.random() + 1).toString(36).substring(7)}`;

  // Copy the photon to a temporary directory
  await fs.copy(`${photonDir}/shell`, `${tempDir}/${name}`);
  // Change the photon name in the metadata.json file
  const metadata = await fs.readJSON(`${tempDir}/${name}/metadata.json`);
  metadata.name = name;
  await fs.writeJSON(`${tempDir}/${name}/metadata.json`, metadata);
  await fs.rename(`${tempDir}/${name}/obj.pkl.keep`, `${tempDir}/${name}/obj.pkl`);
  // Zip the photon
  const output = fs.createWriteStream(`${tempDir}/${name}.zip`);
  const archive = archiver("zip", {
    zlib: { level: 9 }, // Sets the compression level.
  });
  archive.pipe(output);
  archive.directory(`${tempDir}/${name}`, false);
  await archive.finalize();

  await fs.remove(`${tempDir}/${name}`);

  // Return the path to the zipped photon
  console.log(name);
  console.log(path.relative(process.cwd(), path.resolve(`${tempDir}`, `${name}.zip`)));
  process.exit(0);
};

/**
 * --create, generate a random photon
 * --remove <name>, remove a specific photon from the temp directory
 * --clean, remove all random photons from the temp directory
 */
const args = process.argv.slice(2);
if (args[0] === "--create") {
    genRandomPhoton();
} else if (args[0] === "--clean") {
    fs.remove(tempDir);
} else if (args[0] === "--remove") {
    fs.remove(`${tempDir}/${args[1]}`);
} else {
    process.stdout.write("Invalid arguments");
    process.exit(1);
}
