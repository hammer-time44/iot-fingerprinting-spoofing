// Host State Machine with 2-tick hysteresis for Network Defense Lab

import { generateFirewallRules } from './firewall';
import { VERDICT_TO_STATE, ACTION_ALLOW, ACTION_QUARANTINE, ACTION_ISOLATE, ACTION_OBSERVE } from './policy';

export class HostStateMachine {
  constructor({
    hostId,
    claimedDevice,
    ip = '192.168.1.100',
    mac = '00:00:00:00:00:00',
    hysteresis = 2
  }) {
    this.hostId = hostId;
    this.claimedDevice = claimedDevice;
    this.ip = ip;
    this.mac = mac;
    this.hysteresis = hysteresis;

    this.currentState = 'OBSERVING';
    this.pendingVerdict = null;
    this.pendingCount = 0;

    this.windowHistory = [];
    this.verdictHistory = [];
    this.stateHistory = ['OBSERVING'];
    this.timeInStates = {
      OBSERVING: 0,
      TRUSTED: 0,
      QUARANTINED: 0,
      ISOLATED: 0
    };

    this.firewallRules = generateFirewallRules({
      action: ACTION_OBSERVE,
      ip: this.ip,
      mac: this.mac,
      claimedDevice: this.claimedDevice
    });
  }

  reset() {
    this.currentState = 'OBSERVING';
    this.pendingVerdict = null;
    this.pendingCount = 0;
    this.windowHistory = [];
    this.verdictHistory = [];
    this.stateHistory = ['OBSERVING'];
    this.timeInStates = {
      OBSERVING: 0,
      TRUSTED: 0,
      QUARANTINED: 0,
      ISOLATED: 0
    };
    this.firewallRules = generateFirewallRules({
      action: ACTION_OBSERVE,
      ip: this.ip,
      mac: this.mac,
      claimedDevice: this.claimedDevice
    });
  }

  update(deviceLevelVerdict, confidence = 0.0, predictedDevice = '') {
    this.timeInStates[this.currentState] = (this.timeInStates[this.currentState] || 0) + 1;
    this.verdictHistory.push(deviceLevelVerdict);
    let transitioned = false;
    const previousState = this.currentState;

    if (VERDICT_TO_STATE[deviceLevelVerdict]) {
      const targetState = VERDICT_TO_STATE[deviceLevelVerdict];

      if (this.pendingVerdict === targetState) {
        this.pendingCount += 1;
      } else {
        this.pendingVerdict = targetState;
        this.pendingCount = 1;
      }

      if (this.pendingCount >= this.hysteresis) {
        if (this.currentState !== targetState) {
          this.currentState = targetState;
          transitioned = true;
          this.stateHistory.push(targetState);
        }
      }
    } else {
      this.pendingVerdict = null;
      this.pendingCount = 0;
    }

    let action = ACTION_OBSERVE;
    let alert = false;

    if (this.currentState === 'TRUSTED') {
      action = ACTION_ALLOW;
      alert = false;
    } else if (this.currentState === 'QUARANTINED') {
      action = ACTION_QUARANTINE;
      alert = true;
    } else if (this.currentState === 'ISOLATED') {
      action = ACTION_ISOLATE;
      alert = true;
    } else {
      action = ACTION_OBSERVE;
      alert = false;
    }

    this.firewallRules = generateFirewallRules({
      action,
      ip: this.ip,
      mac: this.mac,
      claimedDevice: this.claimedDevice,
      targetDevice: predictedDevice,
      confidence
    });

    return {
      hostId: this.hostId,
      currentState: this.currentState,
      previousState,
      transitioned,
      action,
      alert,
      pendingVerdict: this.pendingVerdict,
      pendingCount: this.pendingCount,
      firewallRules: this.firewallRules
    };
  }
}

