#!/usr/bin/env node
// Project-local Archify workflow for docs/architecture/.
//
// The installed Archify skill is never modified. It has no option to keep
// `visual-check` sidecars out of the delivered directory, so this wrapper owns
// the whole loop: generate, patch wheel zoom into the delivered viewer, drop
// the visual-check artifacts, and verify the result in headless Chrome.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, 'docs', 'architecture');
const sourcesDir = path.join(outDir, 'sources');
const skillRoot = path.join(process.env.USERPROFILE || os.homedir(), '.agents', 'skills', 'archify');
const archifyBin = path.join(skillRoot, 'bin', 'archify.mjs');
const chrome = process.env.ARCHIFY_CHROME
  || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const QUALITY = 'showcase';
const MARKER = 'archify-wheel-zoom';

function fail(message) {
  console.error(message);
  process.exit(1);
}

function targets() {
  if (!fs.existsSync(archifyBin)) {
    fail(
      `Archify skill not found at ${archifyBin}\n` +
      'Install it with:\n' +
      '  npx -y skills add tt-a1i/archify --skill archify --agent opencode --global --copy --yes',
    );
  }
  const names = fs.readdirSync(sourcesDir).filter((name) => name.endsWith('.json')).sort();
  if (!names.length) fail(`No sources found in ${sourcesDir}`);
  return names.map((name) => ({
    label: name.replace(/\.architecture\.json$/, ''),
    source: path.join(sourcesDir, name),
    html: path.join(outDir, name.replace(/\.json$/, '.html')),
  }));
}

function archify(args, { json = false } = {}) {
  const res = spawnSync(process.execPath, [archifyBin, ...args, ...(json ? ['--json'] : [])], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  });
  if (res.error) fail(res.error.message);
  return {
    status: res.status,
    stdout: res.stdout || '',
    stderr: res.stderr || '',
  };
}

// Wheel zoom is absent from the delivered viewer; it is patched in here because
// the Archify skill install is shared and must stay untouched.
const WHEEL_ZOOM = `<script>
/* ${MARKER}: project-local wheel zoom for the delivered Archify viewer. */
(function () {
  var container = document.querySelector('.diagram-container');
  if (!container) return;
  var pending = 0;
  var last = 0;
  container.addEventListener('wheel', function (event) {
    if (event.ctrlKey || event.metaKey) return;
    if (window.innerWidth <= 720 && container.hasAttribute('data-wide-diagram')) return;
    event.preventDefault();
    var unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1;
    var now = Date.now();
    if (now - last > 200) pending = 0;
    last = now;
    pending += event.deltaY * unit;
    if (Math.abs(pending) < 60) return;
    var down = pending > 0;
    pending = 0;
    if (!window.Archify || !Archify.view) return;
    if (down) Archify.view.zoomOut();
    else Archify.view.zoomIn();
  }, { passive: false });
})();
</script>
`;

const SELFTEST = `<script>
(function () {
  var results = {};
  var container = document.querySelector('.diagram-container');
  var view = window.Archify && Archify.view;
  results.ready = !!view;
  if (view && container) {
    var input = container.querySelector('[data-view="in"]');
    var output = container.querySelector('[data-view="out"]');
    var reset = container.querySelector('[data-view="reset"]');
    results.controls = !!(input && output && reset);
    results.initialScale = view.state().scale;
    var wheelIn = new WheelEvent('wheel', { deltaY: -120, bubbles: true, cancelable: true });
    container.dispatchEvent(wheelIn);
    results.wheelPrevented = wheelIn.defaultPrevented;
    results.afterWheelIn = view.state().scale;
    input.click();
    results.afterZoomIn = view.state().scale;
    output.click();
    results.afterZoomOut = view.state().scale;
    var before = view.state();
    container.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0, clientX: 400, clientY: 300, pointerId: 7 }));
    container.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, button: 0, clientX: 470, clientY: 345, pointerId: 7 }));
    container.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, button: 0, clientX: 470, clientY: 345, pointerId: 7 }));
    var after = view.state();
    results.panned = after.x !== before.x || after.y !== before.y;
    reset.click();
    results.afterReset = view.state().scale;
    var wheelOut = new WheelEvent('wheel', { deltaY: 120, bubbles: true, cancelable: true });
    container.dispatchEvent(wheelOut);
    results.wheelOutAtMinPrevented = wheelOut.defaultPrevented;
    results.afterWheelOutAtMin = view.state().scale;
  }
  var node = document.createElement('div');
  node.id = 'archify-selftest-result';
  node.textContent = JSON.stringify(results);
  document.body.appendChild(node);
})();
</script>
`;

const EXPECTED = {
  ready: true,
  controls: true,
  initialScale: 1,
  wheelPrevented: true,
  afterWheelIn: 1.25,
  afterZoomIn: 1.5,
  afterZoomOut: 1.25,
  panned: true,
  afterReset: 1,
  wheelOutAtMinPrevented: true,
  afterWheelOutAtMin: 1,
};

function withSnippet(html, snippet) {
  const at = html.lastIndexOf('</body>');
  return at < 0 ? null : `${html.slice(0, at)}${snippet}${html.slice(at)}`;
}

function inject(html) {
  const text = fs.readFileSync(html, 'utf8');
  if (text.includes(MARKER)) return false;
  const patched = withSnippet(text, WHEEL_ZOOM);
  if (!patched) fail(`No </body> found in ${html}`);
  fs.writeFileSync(html, patched);
  return true;
}

function clean() {
  const junk = fs.readdirSync(outDir).filter((name) => /\.visual-check(\.|$)/.test(name));
  for (const name of junk) fs.unlinkSync(path.join(outDir, name));
  return junk.length;
}

function build() {
  for (const target of targets()) {
    for (const [stage, args] of [
      ['validate', ['validate', 'architecture', target.source, '--quality', QUALITY]],
      ['deliver', ['deliver', 'architecture', target.source, target.html, '--quality', QUALITY]],
    ]) {
      const res = archify(args);
      const line = res.stdout.trim().split('\n').pop() || res.stderr.trim();
      if (res.status !== 0) fail(`${stage} failed for ${target.label}\n${res.stdout}${res.stderr}`);
      console.log(line);
      if (stage === 'deliver' && inject(target.html)) {
        console.log(`wheel zoom patched ${path.basename(target.html)}`);
      }
    }
  }
  const removed = clean();
  if (removed) console.log(`removed ${removed} visual-check artifact(s)`);
}

function verifyOne(target) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-verify-'));
  try {
    const copy = path.join(temp, path.basename(target.html));
    const patched = withSnippet(fs.readFileSync(target.html, 'utf8'), SELFTEST);
    if (!patched) fail(`No </body> found in ${target.html}`);
    fs.writeFileSync(copy, patched);
    const res = spawnSync(chrome, [
      '--headless=new',
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      '--hide-scrollbars',
      '--mute-audio',
      `--user-data-dir=${path.join(temp, 'profile')}`,
      '--dump-dom',
      pathToFileURL(copy).href,
    ], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
    const match = (res.stdout || '').match(/<div id="archify-selftest-result">([^<]*)<\/div>/);
    if (!match) {
      fail(`${target.label}: self-test produced no result\n${(res.stderr || '').slice(-800)}`);
    }
    const results = JSON.parse(match[1]);
    const bad = Object.entries(EXPECTED)
      .filter(([key, value]) => !Object.is(results[key], value))
      .map(([key]) => `${key}: expected ${EXPECTED[key]}, got ${results[key]}`);
    if (bad.length) fail(`${target.label} interaction check failed\n  ${bad.join('\n  ')}`);
    console.log(`${target.label} ok zoom=${results.afterWheelIn} pan x/y moved=${results.panned} reset=${results.afterReset}`);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

function verify() {
  if (!fs.existsSync(chrome)) fail(`Chrome not found at ${chrome}; set ARCHIFY_CHROME.`);
  for (const target of targets()) verifyOne(target);
}

function visualCheck() {
  for (const target of targets()) {
    const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-visual-'));
    try {
      // Run against a copy so Archify's sidecars never land in docs/architecture/.
      const copy = path.join(temp, path.basename(target.html));
      fs.copyFileSync(target.html, copy);
      const res = archify(['visual-check', copy], { json: true });
      let receipt = null;
      try {
        receipt = JSON.parse(res.stdout);
      } catch {
        receipt = null;
      }
      if (!receipt || receipt.status !== 'pass') {
        fail(`${target.label} visual-check ${receipt?.status || 'error'}\n${res.stdout}${res.stderr}`);
      }
      console.log(`${target.label} visual-check pass (${receipt.containment.viewports.length} viewports)`);
    } finally {
      fs.rmSync(temp, { recursive: true, force: true });
    }
  }
}

const command = process.argv[2] || 'build';
if (command === 'build') build();
else if (command === 'verify') verify();
else if (command === 'visual-check') visualCheck();
else fail('Usage: node scripts/archify.mjs [build|verify|visual-check]');
