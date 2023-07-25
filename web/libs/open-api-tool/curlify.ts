// Rewritten from: https://github.com/swagger-api/swagger-ui/blob/master/src/core/plugins/request-snippets/fn.js
// Generate curl command from request object

import {
  OpenAPIRequest,
  RequestWithObjectBody,
} from "@lepton-libs/open-api-tool/interface";

const win =
  typeof window !== "undefined"
    ? window
    : {
        File: function () {
          /* noop */
        } as unknown as File,
      };

/**
 * if duplicate key name existed from FormData entries,
 * we mutated the key name by appending a hashIdx
 * @param {String} k - possibly mutated key name
 * @return {String} - src key name
 */
const extractKey = (k: string) => {
  const hashIdx = "_**[]";
  if (k.indexOf(hashIdx) < 0) {
    return k;
  }
  return k.split(hashIdx)[0].trim();
};

const escapeShell = (str: string) => {
  if (str === "-d ") {
    return str;
  }

  // use double quotes if the string contains a shell variable
  if (/\$.+/.test(str)) {
    return `"${str}"`;
  }

  // eslint-disable-next-line no-useless-escape
  if (!/^[_\/-]/g.test(str)) return "'" + str.replace(/'/g, "'\\''") + "'";
  else return str;
};

const escapeCMD = (str: string) => {
  str = str
    .replace(/\^/g, "^^")
    .replace(/\\"/g, '\\\\"')
    .replace(/"/g, '""')
    .replace(/\n/g, "^\n");
  if (str === "-d ") {
    return str.replace(/-d /g, "-d ^\n");
  }
  // eslint-disable-next-line no-useless-escape
  if (!/^[_\/-]/g.test(str)) return '"' + str + '"';
  else return str;
};

const escapePowershell = (str: string) => {
  if (str === "-d ") {
    return str;
  }
  if (/\n/.test(str)) {
    return (
      '@"\n' +
      str.replace(/"/g, '\\"').replace(/`/g, "``").replace(/\$/, "`$") +
      '\n"@'
    );
  }
  // eslint-disable-next-line no-useless-escape
  if (!/^[_\/-]/g.test(str))
    return "'" + str.replace(/"/g, '""').replace(/'/g, "''") + "'";
  else return str;
};

const isJSONObject = (obj: unknown): obj is RequestWithObjectBody => {
  return typeof obj === "object" && obj !== null && !Array.isArray(obj);
};

const getStringBodyOfMap = (request: RequestWithObjectBody) => {
  const curlifyToJoin = [];
  for (const [k, v] of Object.entries(request.body)) {
    const extractedKey = extractKey(k);
    if (v instanceof win.File) {
      curlifyToJoin.push(
        `  "${extractedKey}": {\n    "name": "${v.name}"${
          v.type ? `,\n    "type": "${v.type}"` : ""
        }\n  }`
      );
    } else {
      curlifyToJoin.push(
        `  "${extractedKey}": ${JSON.stringify(v, null, 2).replace(
          /(\r\n|\r|\n)/g,
          "\n  "
        )}`
      );
    }
  }
  return `{\n${curlifyToJoin.join(",\n")}\n}`;
};

const curlify = (
  request: OpenAPIRequest,
  escape: (v: string) => string,
  newLine: string,
  ext = ""
) => {
  let isMultipartFormDataRequest = false;
  let curlified = "";
  const addWords = (...args: string[]) =>
    (curlified += " " + args.map(escape).join(" "));
  const addWordsWithoutLeadingSpace = (...args: string[]) =>
    (curlified += args.map(escape).join(" "));
  const addNewLine = () => (curlified += ` ${newLine}`);
  const addIndent = (level = 1) => (curlified += "  ".repeat(level));
  const headers = request.headers;
  curlified += "curl" + ext;

  if (request.curlOptions && Array.isArray(request.curlOptions)) {
    addWords(...request.curlOptions);
  }

  addWords("-X", request.method);

  addNewLine();
  addIndent();
  addWordsWithoutLeadingSpace(`${request.url}`);

  if (headers && Object.keys(headers).length) {
    for (const p of Object.entries(request.headers)) {
      addNewLine();
      addIndent();
      const [h, v] = p;
      addWordsWithoutLeadingSpace("-H", `${h}: ${v}`);
      isMultipartFormDataRequest =
        isMultipartFormDataRequest ||
        (/^content-type$/i.test(h) && /^multipart\/form-data$/i.test(v));
    }
  }

  const body = request.body;
  if (body) {
    if (
      isMultipartFormDataRequest &&
      ["POST", "PUT", "PATCH"].includes(request.method)
    ) {
      for (const [k, v] of Object.entries(body)) {
        const extractedKey = extractKey(k);
        addNewLine();
        addIndent();
        addWordsWithoutLeadingSpace("-F");
        if (v instanceof win.File) {
          addWords(
            `${extractedKey}=@${v.name}${v.type ? `;type=${v.type}` : ""}`
          );
        } else {
          addWords(`${extractedKey}=${v}`);
        }
      }
    } else if (body instanceof win.File) {
      addNewLine();
      addIndent();
      addWordsWithoutLeadingSpace(`--data-binary '@${body.name}'`);
    } else {
      addNewLine();
      addIndent();
      addWordsWithoutLeadingSpace("-d ");
      let reqBody = body;
      if (!isJSONObject(reqBody)) {
        if (typeof reqBody !== "string") {
          reqBody = JSON.stringify(reqBody);
        }
        addWordsWithoutLeadingSpace(reqBody);
      } else {
        addWordsWithoutLeadingSpace(
          getStringBodyOfMap(request as RequestWithObjectBody)
        );
      }
    }
  } else if (!body && request.method === "POST") {
    addNewLine();
    addIndent();
    addWordsWithoutLeadingSpace("-d ''");
  }

  return curlified;
};

export const curlPowershell = (request: OpenAPIRequest) => {
  return curlify(request, escapePowershell, "`\n", ".exe");
};

export const curlBash = (request: OpenAPIRequest) => {
  return curlify(request, escapeShell, "\\\n");
};

export const curlCmd = (request: OpenAPIRequest) => {
  return curlify(request, escapeCMD, "^\n");
};
