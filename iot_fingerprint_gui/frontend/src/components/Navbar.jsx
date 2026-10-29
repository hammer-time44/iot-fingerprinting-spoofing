import React from 'react';
import { Shield, Moon, Sun, Cpu } from 'lucide-react';

export default function Navbar({ darkMode, setDarkMode, threshold = 0.84 }) {
  return (
    <header className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-600 text-white rounded-lg shadow-sm">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white leading-tight">
              Encrypted IoT Device Fingerprinting
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Traffic Timing Analysis & Open-Set Classification &middot; UNSW Benchmark
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center px-2.5 py-1 bg-gray-100 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300">
            <Cpu className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
            <span>Random Forest (100 trees)</span>
          </div>

          <div className="flex items-center px-2.5 py-1 bg-gray-100 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300">
            <span>Threshold: <strong className="font-mono text-gray-900 dark:text-white">{threshold.toFixed(2)}</strong></span>
          </div>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 transition-colors"
            title="Toggle Dark / Light Mode"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>

    </header>
  );
}
