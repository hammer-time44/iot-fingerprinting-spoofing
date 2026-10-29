import React from 'react';

const DEVICE_LABELS = {
  AmazonEcho: 'Amazon Echo',
  BelkinWemoMotionSensor: 'Belkin WeMo Motion',
  PhilipsHue: 'Philips Hue Bridge',
  SamsungCamera: 'Samsung SmartCam',
  TPLinkSmartPlug: 'TP-Link Smart Plug'
};

export default function ProbabilityBars({ probs = {}, dominant = '' }) {
  const classes = ['AmazonEcho', 'BelkinWemoMotionSensor', 'PhilipsHue', 'SamsungCamera', 'TPLinkSmartPlug'];

  return (
    <div className="space-y-2 text-xs">
      {classes.map((cls) => {
        const p = probs[cls] !== undefined ? probs[cls] : 0.0;
        const pct = (p * 100).toFixed(1);
        const isTop = cls === dominant;

        return (
          <div key={cls} className="space-y-1">
            <div className="flex justify-between text-gray-700 dark:text-gray-300">
              <span className={isTop ? 'font-bold text-indigo-600 dark:text-indigo-400' : ''}>
                {DEVICE_LABELS[cls] || cls}
              </span>
              <span className={`font-mono ${isTop ? 'font-bold text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400'}`}>
                {pct}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 h-1.5 rounded-full overflow-hidden">
              <div
                className="h-full transition-all duration-300 rounded-full bg-indigo-600 dark:bg-indigo-500 shadow-sm"
                style={{ width: `${p > 0 ? Math.max(p * 100, 1) : 0}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
