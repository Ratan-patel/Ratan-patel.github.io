#!/usr/bin/env node
/**
 * Static gate for the HTML/JS that ships inside the APK.
 *
 * Every <script> block is parsed by the VM before the build runs, because a syntax error in a
 * bundled page is invisible to Gradle — the APK would build happily and the app would open to a
 * blank screen. Marker assertions then confirm the bridge contract is still wired up.
 *
 *   node apps/ratan-ai-agent/tools/check_web_assets.js <file.html> [more.html ...]
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const REQUIREMENTS = {
  'home.html': [
    'RatanBridge', 'AirTBridge', '__offlineNotice', '__permissionResult', '__status',
    'openToolkit', 'openAgent', 'selfTest', 'setPref', 'requestLocalNetworkPermission',
    'llmInfo', 'llmSetKey', 'llmClearKey', 'llmSaveConfig', 'llmTest', 'llmChatAsync',
    '__llmCallback', '{{MESSAGES}}', '{{KEY}}',
  ],
  'toolkit.html': ['AirTBridge', 'AIRT', 'owasp', 'LLM01'],
};

let failures = 0;

function fail(message) {
  failures += 1;
  console.error(`  ✗ ${message}`);
}

for (const file of process.argv.slice(2)) {
  if (!fs.existsSync(file)) {
    fail(`${file}: not found`);
    continue;
  }
  const html = fs.readFileSync(file, 'utf8');
  const name = path.basename(file);
  const sizeKb = (Buffer.byteLength(html, 'utf8') / 1024).toFixed(1);
  console.log(`${name} (${sizeKb} KB)`);

  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]);
  if (scripts.length === 0) {
    fail(`${name}: no <script> blocks found — is this really the app page?`);
  }
  scripts.forEach((code, index) => {
    try {
      new vm.Script(code, { filename: `${name}#script${index}` });
    } catch (error) {
      fail(`${name} script #${index} syntax error: ${error.message}`);
    }
  });

  for (const marker of REQUIREMENTS[name] || []) {
    if (!html.includes(marker)) {
      fail(`${name}: required marker '${marker}' is missing`);
    }
  }

  const openTags = (html.match(/<script\b/gi) || []).length;
  if (openTags !== scripts.length) {
    fail(`${name}: unbalanced <script> tags (${openTags} open, ${scripts.length} closed)`);
  }
}

if (failures > 0) {
  console.error(`\nweb asset check failed: ${failures} problem(s)`);
  process.exit(1);
}
console.log('\nweb asset check passed');
