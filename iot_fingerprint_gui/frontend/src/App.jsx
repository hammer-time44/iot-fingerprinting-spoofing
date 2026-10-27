import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import TabKnown from './components/TabKnown';
import TabUnknown from './components/TabUnknown';
import TabTestOwn from './components/TabTestOwn';
import SpoofCheck from './components/SpoofCheck';
import { Layers, HelpCircle, HardDrive, ShieldAlert } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('known'); // 'known' | 'unknown' | 'test' | 'spoof'
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark';
  });
  const [threshold, setThreshold] = useState(0.84); // Calibrated default

  // Dark mode effect
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col transition-colors">
      {/* Top Navbar */}
      <Navbar darkMode={darkMode} setDarkMode={setDarkMode} threshold={threshold} />

      {/* Main Tab Bar */}
      <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8 overflow-x-auto">
            <button
              onClick={() => setActiveTab('known')}
              className={`flex items-center space-x-2 py-3.5 border-b-2 text-xs sm:text-sm font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'known'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Known Devices (5)</span>
            </button>

            <button
              onClick={() => setActiveTab('unknown')}
              className={`flex items-center space-x-2 py-3.5 border-b-2 text-xs sm:text-sm font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'unknown'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>Unknown Devices (22)</span>
            </button>

            <button
              onClick={() => setActiveTab('test')}
              className={`flex items-center space-x-2 py-3.5 border-b-2 text-xs sm:text-sm font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'test'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <HardDrive className="w-4 h-4" />
              <span>Test Your Own Device</span>
            </button>

            <button
              onClick={() => setActiveTab('spoof')}
              className={`flex items-center space-x-2 py-3.5 border-b-2 text-xs sm:text-sm font-semibold transition-colors whitespace-nowrap ${
                activeTab === 'spoof'
                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Spoofing Detection</span>
            </button>
          </div>
        </div>
      </nav>

      {/* Tab Content Container */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        {activeTab === 'known' && <TabKnown threshold={threshold} />}
        {activeTab === 'unknown' && <TabUnknown threshold={threshold} setThreshold={setThreshold} />}
        {activeTab === 'test' && <TabTestOwn threshold={threshold} />}
        {activeTab === 'spoof' && <SpoofCheck globalThreshold={threshold} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-4 px-4 text-center text-xs text-gray-500 dark:text-gray-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-2">
          <div>
            Encrypted IoT Device Fingerprinting &middot; Model: Random Forest (100 Trees) &middot; 13 Timing Moments
          </div>
          <div>
            Pipeline: <code>log1p(IAT) &rarr; 128 pkts &rarr; Z-Score &rarr; Top-Confidence Threshold ({threshold.toFixed(2)})</code>
          </div>
        </div>
      </footer>
    </div>
  );
}
