// Read-only checks of live Vite module responses, not browser interactions.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

async function read(url, expectedType) {
  const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  const type = response.headers.get('content-type') || '';
  if (!expectedType.test(type)) throw new Error(`${url} returned unexpected content type: ${type}`);
  return response.text();
}

function imports(program) {
  const pending = [program], sources = [];
  while (pending.length) {
    const node = pending.pop();
    if (!node || typeof node !== 'object') continue;
    if (['ImportDeclaration', 'ExportNamedDeclaration', 'ExportAllDeclaration', 'ImportExpression'].includes(node.type)
        && typeof node.source?.value === 'string') sources.push(node.source.value);
    for (const value of Object.values(node)) {
      if (value && typeof value === 'object') pending.push(...(Array.isArray(value) ? value : [value]));
    }
  }
  return sources;
}

async function checkPortal(port) {
  const directory = port === 5174 ? 'government_portal' : 'user_portal';
  const require = createRequire(new URL(`../${directory}/package.json`, import.meta.url));
  const { parseAst } = await import(pathToFileURL(require.resolve('rolldown/parseAst')));
  const base = new URL(`http://127.0.0.1:${port}/`);
  const html = await read(base, /^text\/html\b/);
  const pending = [], checked = new Set();
  for (const match of html.matchAll(/<script\b([^>]*)>/gi)) {
    const attrs = Object.fromEntries([...match[1].matchAll(/([\w-]+)\s*=\s*(["'])(.*?)\2/g)].map((item) => [item[1], item[3]]));
    if (attrs.type === 'module' && attrs.src) pending.push(new URL(attrs.src, base).href);
  }
  if (!pending.length) throw new Error(`${base} has no module entrypoint`);
  while (pending.length) {
    const url = pending.shift();
    if (checked.has(url)) continue;
    const source = await read(url, /^(?:text|application)\/javascript\b/);
    checked.add(url);
    if (checked.size > 1000) throw new Error(`${base} import graph exceeded 1000 modules`);
    for (const specifier of imports(parseAst(source))) {
      if (!/^(\/|\.\.?\/)/.test(specifier)) continue;
      const dependency = new URL(specifier, url);
      if (dependency.origin === base.origin) pending.push(dependency.href);
    }
  }
  return { port, modules_checked: checked.size };
}

const { values } = parseArgs({ options: { port: { type: 'string', multiple: true }, json: { type: 'boolean' } } });
try {
  const results = [];
  for (const port of values.port || ['5173', '5174']) results.push(await checkPortal(Number(port)));
  if (values.json) console.log(JSON.stringify(results));
  else for (const result of results) console.log(`Portal ${result.port}: ${result.modules_checked} live modules loaded successfully`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
