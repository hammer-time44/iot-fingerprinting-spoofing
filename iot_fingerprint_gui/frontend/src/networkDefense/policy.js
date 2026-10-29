// Response policy and 3-identity verdict logic for Network Defense Lab

export const ACTION_ALLOW = 'ALLOW';
export const ACTION_QUARANTINE = 'QUARANTINE';
export const ACTION_ISOLATE = 'ISOLATE';
export const ACTION_OBSERVE = 'OBSERVE';

export const POLICY_MAP = {
  VERIFIED: {
    action: ACTION_ALLOW,
    alert: false,
    description: 'Timing signature verified against claimed identity. Full traffic forwarding allowed.'
  },
  SPOOF_SUSPECTED: {
    action: ACTION_QUARANTINE,
    alert: true,
    description: 'High-confidence behavioral mismatch detected. Host quarantined and redirected to captive portal.'
  },
  UNKNOWN_HARDWARE: {
    action: ACTION_ISOLATE,
    alert: true,
    description: 'Confidence below tau threshold (unseen device signature). Host isolated to containment VLAN 99.'
  },
  INSUFFICIENT_DATA: {
    action: ACTION_OBSERVE,
    alert: false,
    description: 'Awaiting minimum 5 windows for device-level decision. Host monitored under rate limiting.'
  }
};

export const VERDICT_TO_STATE = {
  VERIFIED: 'TRUSTED',
  SPOOF_SUSPECTED: 'QUARANTINED',
  UNKNOWN_HARDWARE: 'ISOLATED',
  INSUFFICIENT_DATA: 'OBSERVING'
};

/**
 * Evaluate single-window 3-identity verdict.
 * @param {Object} probs - { AmazonEcho: 0.95, ... }
 * @param {string} claimedDevice - Registered device name
 * @param {number} tau - Confidence threshold (default 0.84)
 */
export function evaluateWindowVerdict(probs, claimedDevice, tau = 0.84) {
  const entries = Object.entries(probs);
  if (entries.length === 0) {
    return { verdict: 'INSUFFICIENT_DATA', confidence: 0, topClass: null };
  }

  let topClass = entries[0][0];
  let maxP = entries[0][1];

  for (let i = 1; i < entries.length; i++) {
    if (entries[i][1] > maxP) {
      maxP = entries[i][1];
      topClass = entries[i][0];
    }
  }

  const confidence = Number(maxP.toFixed(4));
  let verdict;

  if (confidence < tau) {
    verdict = 'UNKNOWN_HARDWARE';
  } else if (topClass === claimedDevice) {
    verdict = 'VERIFIED';
  } else {
    verdict = 'SPOOF_SUSPECTED';
  }

  return { verdict, confidence, topClass };
}

/**
 * Compute multi-window device-level aggregate verdict over last n windows.
 * @param {Array<Object>} windowResults - Array of probability dicts or window result objects
 * @param {string} claimedDevice - Registered device name
 * @param {number} nWindows - Number of windows to aggregate (default 5)
 * @param {number} tau - Confidence threshold (default 0.84)
 */
export function aggregateDeviceVerdict(windowResults, claimedDevice, nWindows = 5, tau = 0.84) {
  if (!windowResults || windowResults.length < nWindows) {
    return {
      verdict: 'INSUFFICIENT_DATA',
      confidence: 0,
      topClass: null,
      meanProbs: {},
      windowCount: windowResults ? windowResults.length : 0
    };
  }

  const lastN = windowResults.slice(-nWindows);
  const classes = Object.keys(lastN[0].probs || lastN[0]);
  const meanProbs = {};

  classes.forEach((cls) => {
    let sum = 0;
    lastN.forEach((w) => {
      const p = w.probs ? w.probs[cls] : w[cls];
      sum += (p || 0);
    });
    meanProbs[cls] = Number((sum / nWindows).toFixed(4));
  });

  let topClass = classes[0];
  let maxP = meanProbs[classes[0]];

  for (let i = 1; i < classes.length; i++) {
    if (meanProbs[classes[i]] > maxP) {
      maxP = meanProbs[classes[i]];
      topClass = classes[i];
    }
  }

  const confidence = Number(maxP.toFixed(4));
  let verdict;

  if (confidence < tau) {
    verdict = 'UNKNOWN_HARDWARE';
  } else if (topClass === claimedDevice) {
    verdict = 'VERIFIED';
  } else {
    verdict = 'SPOOF_SUSPECTED';
  }

  return {
    verdict,
    confidence,
    topClass,
    meanProbs,
    windowCount: windowResults.length
  };
}

/**
 * Pure function: maps a verdict to its policy action and state.
 */
export function evaluatePolicy(verdict) {
  if (POLICY_MAP[verdict]) {
    return {
      action: POLICY_MAP[verdict].action,
      alert: POLICY_MAP[verdict].alert,
      description: POLICY_MAP[verdict].description,
      state: VERDICT_TO_STATE[verdict] || 'OBSERVING'
    };
  }
  return {
    action: ACTION_ISOLATE,
    alert: true,
    description: `Unrecognized verdict '${verdict}'. Safe isolation fallback applied.`,
    state: 'ISOLATED'
  };
}

