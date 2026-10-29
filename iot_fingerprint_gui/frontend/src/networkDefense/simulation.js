// Client-side pure JavaScript simulation engine for Network Defense Lab

import { HostStateMachine } from './stateMachine';
import { evaluateWindowVerdict, aggregateDeviceVerdict } from './policy';

export class ClientSimulation {
  constructor(masterData, onTickCallback) {
    this.masterData = masterData || {};
    this.onTick = onTickCallback;

    this.isRunning = false;
    this.tickCount = 0;
    this.speed = 1.0;
    this.tau = this.masterData.meta?.tau || 0.84;

    this.timerId = null;
    this.scenario = 'BASELINE';
    this.scenarioParams = {
      source_device: 'SamsungCamera',
      claimed_device: 'AmazonEcho',
      unseen_device: 'WithingsSmartScale',
      strength: 0.6,
      hijack_at_tick: 5,
      hijack_device: 'SamsungCamera'
    };

    this.hosts = {};
    this.stateMachines = {};
    this.hostWindowPointers = {};
    this.initHosts();
  }

  initHosts() {
    this.hosts = {};
    this.stateMachines = {};
    this.hostWindowPointers = {};

    const registry = this.masterData.registry || {};
    Object.values(registry).forEach((reg) => {
      this.stateMachines[reg.id] = new HostStateMachine({
        hostId: reg.id,
        claimedDevice: reg.claimed_device,
        ip: reg.ip,
        mac: reg.mac,
        hysteresis: 2
      });

      this.hostWindowPointers[reg.id] = 0;
      this.hosts[reg.id] = {
        id: reg.id,
        display_name: reg.display_name,
        ip: reg.ip,
        mac: reg.mac,
        claimed_device: reg.claimed_device,
        state: 'OBSERVING',
        predicted_device: null,
        confidence: 0,
        probabilities: {},
        device_level_verdict: 'INSUFFICIENT_DATA',
        window_verdict: 'INSUFFICIENT_DATA',
        action: 'OBSERVE',
        sparkline: [2.1, 2.3, 2.0, 2.4, 2.2, 2.1, 2.5, 2.2, 2.3, 2.1],
        firewall_rules: this.stateMachines[reg.id].firewall_rules,
        window_count: 0
      };
    });

    // If scenario includes rogue host, instantiate attacker
    if (this.scenario === 'IMPERSONATION' || this.scenario === 'UNKNOWN_HARDWARE' || this.scenario === 'TIMING_MIMICRY' || this.scenario === 'REPLAY' || this.scenario === 'GENUINE_CONTROL') {
      const attId = 'host-attacker-1';
      const claimedDev = this.scenarioParams.claimed_device || 'AmazonEcho';
      const isGenuine = this.scenario === 'GENUINE_CONTROL' || (this.scenario === 'IMPERSONATION' && this.scenarioParams.source_device === claimedDev);

      this.stateMachines[attId] = new HostStateMachine({
        hostId: attId,
        claimedDevice: claimedDev,
        ip: '192.168.1.200',
        mac: 'DE:AD:BE:EF:00:01',
        hysteresis: 2
      });
      this.hostWindowPointers[attId] = 0;
      this.hosts[attId] = {
        id: attId,
        display_name: isGenuine ? `${claimedDev} (Genuine Control)` : 'Attacker Rogue Host',
        ip: '192.168.1.200',
        mac: 'DE:AD:BE:EF:00:01',
        claimed_device: claimedDev,
        state: 'OBSERVING',
        predicted_device: null,
        confidence: 0,
        probabilities: {},
        device_level_verdict: 'INSUFFICIENT_DATA',
        window_verdict: 'INSUFFICIENT_DATA',
        action: 'OBSERVE',
        sparkline: [3.5, 3.2, 3.8, 3.6, 3.4, 3.7, 3.5, 3.9, 3.3, 3.6],
        firewall_rules: this.stateMachines[attId].firewall_rules,
        window_count: 0
      };
    }
  }

  setScenario(scenario, params = {}) {
    this.scenario = scenario;
    this.scenarioParams = { ...this.scenarioParams, ...params };
    this.reset();
  }

  setTau(tau) {
    this.tau = tau;
  }

  setSpeed(speed) {
    this.speed = speed;
    if (this.isRunning) {
      this.stop();
      this.start();
    }
  }

  start() {
    if (this.isRunning) return;
    this.isRunning = true;
    const intervalMs = Math.max(125, Math.round(1000 / this.speed));
    this.timerId = setInterval(() => this.stepTick(), intervalMs);
  }

  stop() {
    this.isRunning = false;
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  reset() {
    this.stop();
    this.tickCount = 0;
    this.initHosts();
    if (this.onTick) {
      this.onTick({
        tick: 0,
        hosts: this.hosts,
        events: []
      });
    }
  }

  stepTick() {
    this.tickCount += 1;
    const events = [];

    // Process each host
    Object.keys(this.hosts).forEach((hostId) => {
      const host = this.hosts[hostId];
      const sm = this.stateMachines[hostId];

      let windowData = null;

      // Select window source based on scenario and host
      if (hostId.startsWith('host-attacker')) {
        if (this.scenario === 'IMPERSONATION' || this.scenario === 'GENUINE_CONTROL') {
          const srcDev = this.scenarioParams.source_device || 'SamsungCamera';
          const list = this.masterData.legit?.[srcDev] || [];
          if (list.length > 0) {
            windowData = list[this.hostWindowPointers[hostId] % list.length];
          }
        } else if (this.scenario === 'UNKNOWN_HARDWARE') {
          const unseenDev = this.scenarioParams.unseen_device || 'WithingsSmartScale';
          const list = this.masterData.unseen?.[unseenDev] || [];
          if (list.length > 0) {
            windowData = list[this.hostWindowPointers[hostId] % list.length];
          }
        } else if (this.scenario === 'TIMING_MIMICRY') {
          const attDev = this.scenarioParams.source_device || 'SamsungCamera';
          const tgtDev = this.scenarioParams.claimed_device || 'AmazonEcho';
          const sKey = (this.scenarioParams.strength || 0.6).toFixed(1);
          const pairKey = `${attDev}->${tgtDev}`;
          const qList = this.masterData.mimicry?.[pairKey]?.quantile?.[sKey] || [];
          if (qList.length > 0) {
            windowData = qList[this.hostWindowPointers[hostId] % qList.length];
          }
        } else if (this.scenario === 'REPLAY') {
          const tgtDev = this.scenarioParams.claimed_device || 'AmazonEcho';
          const list = this.masterData.legit?.[tgtDev] || [];
          if (list.length > 0) {
            windowData = list[this.hostWindowPointers[hostId] % list.length];
          }
        }
      } else {
        // Legitimate home host
        let targetSrc = host.claimed_device;

        // Hijacked device scenario
        if (this.scenario === 'HIJACKED_DEVICE' && host.claimed_device === 'AmazonEcho' && this.tickCount >= (this.scenarioParams.hijack_at_tick || 5)) {
          targetSrc = this.scenarioParams.hijack_device || 'SamsungCamera';
        }

        const list = this.masterData.legit?.[targetSrc] || [];
        if (list.length > 0) {
          windowData = list[this.hostWindowPointers[hostId] % list.length];
        }
      }

      this.hostWindowPointers[hostId] += 1;

      if (!windowData) return;

      const probs = windowData.probs;
      const winVerdictObj = evaluateWindowVerdict(probs, host.claimed_device, this.tau);

      // Slide into window history
      sm.windowHistory.push({ probs, topClass: winVerdictObj.topClass });
      if (sm.windowHistory.length > 10) sm.windowHistory.shift();

      // Aggregate device-level verdict over last 5 windows
      const devVerdictObj = aggregateDeviceVerdict(sm.windowHistory, host.claimed_device, 5, this.tau);

      // Update state machine
      const smUpdate = sm.update(devVerdictObj.verdict, devVerdictObj.confidence, devVerdictObj.topClass);

      // Update sparkline with real IAT or simulated value
      let newIatVal = 2.0;
      if (windowData.iat && windowData.iat.length > 0) {
        newIatVal = windowData.iat[0];
      } else {
        newIatVal = 1.0 + Math.random() * 2.5;
      }
      const newSparkline = [...host.sparkline.slice(1), Number(newIatVal.toFixed(2))];

      // Update host state
      host.state = smUpdate.currentState;
      host.action = smUpdate.action;
      host.window_verdict = winVerdictObj.verdict;
      host.device_level_verdict = devVerdictObj.verdict;
      host.confidence = devVerdictObj.confidence || winVerdictObj.confidence;
      host.predicted_device = devVerdictObj.topClass || winVerdictObj.topClass;
      host.probabilities = devVerdictObj.meanProbs && Object.keys(devVerdictObj.meanProbs).length > 0 ? devVerdictObj.meanProbs : probs;
      host.sparkline = newSparkline;
      host.firewall_rules = smUpdate.firewallRules;
      host.window_count = sm.windowHistory.length;

      // Log transition events
      if (smUpdate.transitioned) {
        events.push({
          tick: this.tickCount,
          timestamp: new Date().toLocaleTimeString(),
          host_id: host.id,
          host_name: host.display_name,
          claimed_device: host.claimed_device,
          previous_state: smUpdate.previousState,
          new_state: smUpdate.currentState,
          verdict: devVerdictObj.verdict,
          confidence: devVerdictObj.confidence,
          predicted_device: devVerdictObj.topClass,
          action: smUpdate.action,
          rule: smUpdate.firewallRules?.summary || ''
        });
      }
    });

    // Special case for ACCESS_ATTEMPT scenario
    if (this.scenario === 'ACCESS_ATTEMPT' && this.tickCount % 2 === 0) {
      events.push({
        tick: this.tickCount,
        timestamp: new Date().toLocaleTimeString(),
        host_id: 'gateway-firewall',
        host_name: 'WAN Ingress Filter',
        claimed_device: 'External Attacker',
        previous_state: 'FILTERING',
        new_state: 'DROPPED',
        verdict: 'ACCESS_ATTEMPT_DENIED',
        confidence: 1.0,
        predicted_device: 'UNSOLICITED_WAN_PROBE',
        action: 'DEFAULT_DENY',
        rule: 'DEFAULT_DENY: Inbound SYN probe from 198.51.100.42 dropped by perimeter firewall.'
      });
    }

    if (this.onTick) {
      this.onTick({
        tick: this.tickCount,
        hosts: { ...this.hosts },
        events
      });
    }
  }
}

