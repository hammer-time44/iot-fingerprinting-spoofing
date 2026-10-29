// Parity Test: Node.js runner comparing JS implementation against Python parity fixtures

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Import JS modules
import { evaluateWindowVerdict, aggregateDeviceVerdict, evaluatePolicy } from '../../iot_fingerprint_gui/frontend/src/networkDefense/policy.js';
import { generateFirewallRules } from '../../iot_fingerprint_gui/frontend/src/networkDefense/firewall.js';

const fixturesPath = path.resolve(__dirname, 'parity_fixtures.json');
const rawData = fs.readFileSync(fixturesPath, 'utf8');
const { tau, classes, fixtures } = JSON.parse(rawData);

console.log(`=== Testing JS Parity against ${fixtures.length} Python Fixtures ===`);
let passedCount = 0;
let errors = [];

fixtures.forEach((f, idx) => {
  const { id, claimed_device, probs, window_result, device_result, policy, rules } = f;

  // 1. Single window verdict parity
  const win = evaluateWindowVerdict(probs, claimed_device, tau);
  if (win.verdict !== window_result.verdict) {
    errors.push(`[Fixture ${id}] Window verdict mismatch: JS=${win.verdict}, PY=${window_result.verdict}`);
  }
  if (win.topClass !== window_result.top_class) {
    errors.push(`[Fixture ${id}] Window topClass mismatch: JS=${win.topClass}, PY=${window_result.top_class}`);
  }
  if (Math.abs(win.confidence - window_result.confidence) > 1e-3) {
    errors.push(`[Fixture ${id}] Window confidence mismatch: JS=${win.confidence}, PY=${window_result.confidence}`);
  }

  // 2. Policy action parity
  const pol = evaluatePolicy(device_result.verdict);
  if (pol.action !== policy.action) {
    errors.push(`[Fixture ${id}] Policy action mismatch: JS=${pol.action}, PY=${policy.action}`);
  }
  if (pol.state !== policy.state) {
    errors.push(`[Fixture ${id}] Policy state mismatch: JS=${pol.state}, PY=${policy.state}`);
  }
  if (pol.alert !== policy.alert) {
    errors.push(`[Fixture ${id}] Policy alert mismatch: JS=${pol.alert}, PY=${policy.alert}`);
  }

  // 3. Firewall rule text parity
  const hostInfo = {
    action: policy.action,
    ip: `192.168.1.${100 + (idx % 50)}`,
    mac: `00:11:22:33:44:${(idx % 99).toString(16).padStart(2, '0').toUpperCase()}`,
    claimedDevice: claimed_device,
    targetDevice: device_result.top_class,
    confidence: device_result.confidence
  };
  const jsRules = generateFirewallRules(hostInfo);

  if (jsRules.iptables !== rules.iptables) {
    errors.push(`[Fixture ${id}] iptables text mismatch:\nJS:\n${jsRules.iptables}\nPY:\n${rules.iptables}`);
  }
  if (jsRules.nftables !== rules.nftables) {
    errors.push(`[Fixture ${id}] nftables text mismatch:\nJS:\n${jsRules.nftables}\nPY:\n${rules.nftables}`);
  }

  if (errors.length === 0) {
    passedCount++;
  }
});

if (errors.length > 0) {
  console.error(`FAILED: ${errors.length} errors found:`);
  errors.slice(0, 5).forEach((e) => console.error(e));
  process.exit(1);
} else {
  console.log(`SUCCESS: 100% Parity Verified! ${passedCount}/${fixtures.length} fixtures matched Python output exactly.`);
  process.exit(0);
}

