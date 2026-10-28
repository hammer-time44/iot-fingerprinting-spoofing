import React, { useState, useEffect, useRef } from 'react';
import { Upload, Radio, FileText, Download, ShieldAlert, Play, Square, CheckCircle, AlertTriangle, Zap } from 'lucide-react';
import ProbabilityBars from './ProbabilityBars';
import IatTimelineChart from './IatTimelineChart';
import FeaturesTable from './FeaturesTable';
import { SAMPLE_ECHO_TIMESTAMPS, SAMPLE_UNKNOWN_TIMESTAMPS } from '../data/sampleTimestamps';

export default function TabTestOwn({ threshold = 0.84 }) {
  const [deviceName, setDeviceName] = useState('My Test Device');
  const [inputMode, setInputMode] = useState('upload'); // 'upload' | 'live' | 'paste'

  // Upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  // Paste state
  const [timestampText, setTimestampText] = useState('');
  const [pasteLoading, setPasteLoading] = useState(false);
  const [pasteError, setPasteError] = useState('');

  // Live capture state
  const [interfaces, setInterfaces] = useState([]);
  const [selectedInterface, setSelectedInterface] = useState('');
  const [filterMac, setFilterMac] = useState('');
  const [filterIp, setFilterIp] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureStatus, setCaptureStatus] = useState('');
  const [captureError, setCaptureError] = useState('');
  const liveWsRef = useRef(null);

  // Common Results state
  const [resultsData, setResultsData] = useState(null);
  const [inspectedWindowIdx, setInspectedWindowIdx] = useState(0);

  // Load available network interfaces
  useEffect(() => {
    fetch('/api/stream/interfaces')
      .then((res) => res.json())
      .then((data) => {
        if (data.interfaces && data.interfaces.length > 0) {
          setInterfaces(data.interfaces);
          setSelectedInterface(data.interfaces[0]);
        }
      })
      .catch((err) => console.error('Error fetching interfaces:', err));
  }, []);

  // Cleanup Live WebSocket
  useEffect(() => {
    return () => {
      if (liveWsRef.current) {
        liveWsRef.current.close();
      }
    };
  }, []);

  // Handle File Upload
  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please select a .pcap, .pcapng, or .csv file.');
      return;
    }
    setUploadLoading(true);
    setUploadError('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('threshold', threshold.toString());
    formData.append('device_name', deviceName);

    try {
      const res = await fetch('/api/predict/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      setResultsData({
        device_name: deviceName,
        source: `File: ${data.filename} (${data.packet_count} packets)`,
        summary: data.summary,
        windows: data.windows,
      });
      setInspectedWindowIdx(0);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadLoading(false);
    }
  };

  // Sample Timestamp Loaders
  const handleLoadSampleEcho = () => {
    setTimestampText(SAMPLE_ECHO_TIMESTAMPS);
    setDeviceName('Amazon Echo (Pasted Sample)');
    setPasteError('');
  };

  const handleLoadSampleUnknown = () => {
    setTimestampText(SAMPLE_UNKNOWN_TIMESTAMPS);
    setDeviceName('Withings Smart Scale (Unknown Device Sample)');
    setPasteError('');
  };

  // Handle Paste Timestamps
  const handlePasteSubmit = async (e) => {
    e.preventDefault();
    setPasteLoading(true);
    setPasteError('');

    try {
      const parsed = timestampText
        .split(/[\s,]+/)
        .map((v) => parseFloat(v.trim()))
        .filter((v) => !isNaN(v));

      if (parsed.length < 129) {
        throw new Error(
          `Found ${parsed.length} timestamps. Need at least 129 timestamps to form a complete 128-packet window.`
        );
      }

      const res = await fetch('/api/predict/timestamps', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timestamps: parsed, threshold }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Processing failed');
      }

      setResultsData({
        device_name: deviceName,
        source: `Pasted Data (${parsed.length} timestamps)`,
        summary: data.summary,
        windows: data.windows,
      });
      setInspectedWindowIdx(0);
    } catch (err) {
      setPasteError(err.message);
    } finally {
      setPasteLoading(false);
    }
  };

  // Handle Live Capture Toggle
  const toggleLiveCapture = () => {
    if (isCapturing) {
      if (liveWsRef.current) {
        liveWsRef.current.send(JSON.stringify({ action: 'stop' }));
        liveWsRef.current.close();
      }
      setIsCapturing(false);
      setCaptureStatus('Capture stopped.');
    } else {
      setCaptureError('');
      setCaptureStatus('Connecting to packet capture interface...');

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname || '127.0.0.1';
      const queryParams = new URLSearchParams({
        threshold: threshold.toString(),
      });
      if (selectedInterface) queryParams.append('interface', selectedInterface);
      if (filterMac) queryParams.append('filter_mac', filterMac);
      if (filterIp) queryParams.append('filter_ip', filterIp);

      const wsUrl = `${protocol}//${host}:8765/stream/live?${queryParams.toString()}`;

      try {
        const ws = new WebSocket(wsUrl);
        liveWsRef.current = ws;

        ws.onopen = () => {
          setIsCapturing(true);
          setResultsData((prev) => ({
            device_name: deviceName,
            source: `Live Capture on ${selectedInterface || 'Default'}`,
            summary: { device_verdict: 'CAPTURING...', device_label: 'Awaiting 128 packets' },
            windows: [],
          }));
        };

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.type === 'status') {
            setCaptureStatus(msg.message);
          } else if (msg.type === 'window') {
            setResultsData((prev) => {
              const newWindows = [...(prev?.windows || []), msg];
              const confs = newWindows.map((w) => w.top_prob);
              const knowns = newWindows.filter((w) => w.verdict === 'KNOWN');
              const domProfile = msg.closest_profile;

              return {
                device_name: deviceName,
                source: `Live Capture on ${selectedInterface || 'Default'}`,
                summary: {
                  device_verdict: knowns.length > newWindows.length / 2 ? 'KNOWN' : 'UNKNOWN',
                  device_label: knowns.length > newWindows.length / 2 ? domProfile : 'Low Confidence / Unfamiliar',
                  total_windows: newWindows.length,
                  known_windows: knowns.length,
                  mean_confidence: (confs.reduce((a, b) => a + b, 0) / confs.length).toFixed(4),
                },
                windows: newWindows,
              };
            });
            setInspectedWindowIdx((prev) => prev);
          } else if (msg.type === 'error') {
            setCaptureError(msg.message);
            setIsCapturing(false);
          }
        };

        ws.onerror = (err) => {
          setCaptureError('WebSocket capture error: Admin rights or Npcap may be required.');
          setIsCapturing(false);
        };

        ws.onclose = () => {
          setIsCapturing(false);
        };
      } catch (err) {
        setCaptureError(err.message);
        setIsCapturing(false);
      }
    }
  };

  // Export Results
  const exportAsJSON = () => {
    if (!resultsData) return;
    const blob = new Blob([JSON.stringify(resultsData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${deviceName.replace(/\s+/g, '_')}_fingerprint_run.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportAsCSV = () => {
    if (!resultsData || !resultsData.windows || resultsData.windows.length === 0) return;
    const rows = [
      ['Window', 'Verdict', 'Label', 'Closest_Profile', 'Confidence', 'P_Echo', 'P_WeMo', 'P_Hue', 'P_Samsung', 'P_TPLink'],
    ];

    resultsData.windows.forEach((w, idx) => {
      rows.push([
        idx + 1,
        w.verdict,
        w.label,
        w.closest_profile,
        w.top_prob,
        w.probs?.AmazonEcho || 0,
        w.probs?.BelkinWemoMotionSensor || 0,
        w.probs?.PhilipsHue || 0,
        w.probs?.SamsungCamera || 0,
        w.probs?.TPLinkSmartPlug || 0,
      ]);
    });

    const csvContent = rows.map((e) => e.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${deviceName.replace(/\s+/g, '_')}_fingerprint_run.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const inspectedWindow = resultsData?.windows?.[inspectedWindowIdx] || resultsData?.windows?.[0];

  return (
    <div className="space-y-8">
      {/* Intro Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-3">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            Test Your Own Device & Live Traffic
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Feed network captures, live interface streams, or raw timestamps through the 128-packet timing pipeline.
          </p>
        </div>

        {/* Device Name Field */}
        <div className="flex items-center space-x-2">
          <label className="text-xs text-gray-600 dark:text-gray-400 font-medium">Device Label:</label>
          <input
            type="text"
            value={deviceName}
            onChange={(e) => setDeviceName(e.target.value)}
            className="px-3 py-1 text-xs rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-white font-medium focus:ring-1 focus:ring-slate-500"
          />
        </div>
      </div>

      {/* Input Mode Selector */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 space-x-6 text-xs">
        <button
          onClick={() => setInputMode('upload')}
          className={`flex items-center space-x-2 pb-2 font-medium border-b-2 transition-colors ${
            inputMode === 'upload'
              ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
          }`}
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload Capture (.pcap / .csv)</span>
        </button>

        <button
          onClick={() => setInputMode('live')}
          className={`flex items-center space-x-2 pb-2 font-medium border-b-2 transition-colors ${
            inputMode === 'live'
              ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
          }`}
        >
          <Radio className="w-3.5 h-3.5" />
          <span>Live Network Sniffing</span>
        </button>

        <button
          onClick={() => setInputMode('paste')}
          className={`flex items-center space-x-2 pb-2 font-medium border-b-2 transition-colors ${
            inputMode === 'paste'
              ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Paste Timestamps</span>
        </button>
      </div>

      {/* Input Panes */}
      <div className="border border-gray-200 dark:border-gray-800 rounded-lg p-5 bg-white dark:bg-gray-900">
        {/* Mode 1: File Upload */}
        {inputMode === 'upload' && (
          <form onSubmit={handleUploadSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-800 dark:text-gray-200 mb-1">
                Select Packet Capture or Timestamp CSV:
              </label>
              <input
                type="file"
                accept=".pcap,.pcapng,.cap,.csv,.txt"
                onChange={(e) => setSelectedFile(e.target.files[0])}
                className="block w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 cursor-pointer"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Supported: <code>.pcap</code>, <code>.pcapng</code>, and <code>.csv</code> with timestamp column.
                Payloads are completely ignored; only packet arrival timestamps are read.
              </p>
            </div>

            {uploadError && (
              <div className="p-2.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded text-rose-700 dark:text-rose-300 text-xs">
                {uploadError}
              </div>
            )}

            <button
              type="submit"
              disabled={uploadLoading || !selectedFile}
              className="px-4 py-2 bg-indigo-600 text-white rounded text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 shadow-sm"
            >
              {uploadLoading ? 'Processing Windows...' : 'Run Pipeline & Fingerprint'}
            </button>
          </form>
        )}

        {/* Mode 2: Live Network Sniffing */}
        {inputMode === 'live' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Interface:
                </label>
                <select
                  value={selectedInterface}
                  onChange={(e) => setSelectedInterface(e.target.value)}
                  disabled={isCapturing}
                  className="w-full text-xs p-2 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                >
                  {interfaces.map((iface) => (
                    <option key={iface} value={iface}>
                      {iface}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Filter by IP (Optional):
                </label>
                <input
                  type="text"
                  placeholder="e.g. 192.168.1.105"
                  value={filterIp}
                  onChange={(e) => setFilterIp(e.target.value)}
                  disabled={isCapturing}
                  className="w-full text-xs p-2 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Filter by MAC (Optional):
                </label>
                <input
                  type="text"
                  placeholder="e.g. 44:65:0d:56:cc:d3"
                  value={filterMac}
                  onChange={(e) => setFilterMac(e.target.value)}
                  disabled={isCapturing}
                  className="w-full text-xs p-2 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                />
              </div>
            </div>

            {captureStatus && (
              <div className="p-2 bg-slate-50 dark:bg-slate-800/60 rounded text-xs text-slate-700 dark:text-slate-300 font-mono">
                {captureStatus}
              </div>
            )}

            {captureError && (
              <div className="p-2.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded text-rose-700 dark:text-rose-300 text-xs">
                {captureError}
              </div>
            )}

            <button
              onClick={toggleLiveCapture}
              className={`flex items-center space-x-2 px-4 py-2 rounded text-xs font-semibold transition-colors ${
                isCapturing
                  ? 'bg-rose-600 text-white hover:bg-rose-700'
                  : 'bg-slate-900 dark:bg-slate-100 text-white dark:text-gray-900 hover:bg-slate-800'
              }`}
            >
              {isCapturing ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop Live Capture</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Start Live Capture</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Mode 3: Paste Timestamps */}
        {inputMode === 'paste' && (
          <form onSubmit={handlePasteSubmit} className="space-y-4">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <label className="block text-xs font-semibold text-gray-800 dark:text-gray-200">
                  Paste Packet Timestamps (space, comma, or newline-separated):
                </label>
                <div className="flex items-center space-x-3 text-xs">
                  <button
                    type="button"
                    onClick={handleLoadSampleEcho}
                    className="font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center space-x-1 transition-colors cursor-pointer"
                    title="Load 129 authentic packet timestamps from an Amazon Echo"
                  >
                    <span className="text-amber-500">⚡</span>
                    <span>Load Sample Echo Timestamps (129 Packets)</span>
                  </button>
                  <span className="text-gray-300 dark:text-gray-700">|</span>
                  <button
                    type="button"
                    onClick={handleLoadSampleUnknown}
                    className="font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 flex items-center space-x-1 transition-colors cursor-pointer"
                    title="Load 129 authentic packet timestamps from Withings Smart Scale (an unseen device)"
                  >
                    <span className="text-amber-500">⚡</span>
                    <span>Load Unknown Device Sample (129 Packets)</span>
                  </button>
                </div>
              </div>
              <textarea
                rows={4}
                value={timestampText}
                onChange={(e) => setTimestampText(e.target.value)}
                placeholder="1479859200.12345, 1479859200.14562, 1479859200.18942 ... (minimum 129 timestamps required)"
                className="w-full text-xs font-mono p-2.5 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>

            {pasteError && (
              <div className="p-2.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded text-rose-700 dark:text-rose-300 text-xs">
                {pasteError}
              </div>
            )}

            <button
              type="submit"
              disabled={pasteLoading || !timestampText}
              className="px-4 py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-gray-900 rounded text-xs font-semibold hover:bg-slate-800 disabled:opacity-50"
            >
              {pasteLoading ? 'Computing IAT & Classifying...' : 'Classify Pasted Timestamps'}
            </button>
          </form>
        )}
      </div>

      {/* Safety Notice Callout */}
      <div className="flex items-start space-x-3 p-3.5 bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-lg text-xs text-slate-600 dark:text-slate-300">
        <ShieldAlert className="w-4 h-4 text-slate-500 mt-0.5 flex-shrink-0" />
        <div>
          <strong className="text-gray-900 dark:text-white">Safety Notice & Privacy Integrity:</strong> Only capture traffic on networks and devices you own or have explicit permission to test.
          The fingerprinting pipeline inspects <em>inter-arrival timing moments only</em>; packet payloads are never read, decrypted, or stored.
        </div>
      </div>

      {/* Results View */}
      {resultsData && (
        <div className="space-y-6">
          {/* Device-Level Verdict Card */}
          <div className="border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-200 dark:border-gray-800 gap-3">
              <div>
                <span className="text-[11px] font-semibold text-gray-500 uppercase">Device-Level Aggregate Verdict</span>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                  {resultsData.device_name}:{' '}
                  <span
                    className={
                      resultsData.summary.device_verdict === 'KNOWN'
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-amber-600 dark:text-amber-400'
                    }
                  >
                    {resultsData.summary.device_verdict}
                  </span>
                </h3>
                <p className="text-xs text-gray-500">
                  Profile: <strong>{resultsData.summary.device_label}</strong> &middot;{' '}
                  {resultsData.source}
                </p>
              </div>

              {/* Export Buttons */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={exportAsCSV}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 rounded text-xs font-medium text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export CSV</span>
                </button>
                <button
                  onClick={exportAsJSON}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 rounded text-xs font-medium text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export JSON</span>
                </button>
              </div>
            </div>

            {/* Results Table */}
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 text-[11px]">
                    <th className="p-2">Window #</th>
                    <th className="p-2">Verdict</th>
                    <th className="p-2">Assigned Profile</th>
                    <th className="p-2 text-right">Confidence</th>
                    <th className="p-2">Amazon Echo</th>
                    <th className="p-2">Belkin Motion</th>
                    <th className="p-2">Philips Hue</th>
                    <th className="p-2">Samsung Cam</th>
                    <th className="p-2">TP-Link Plug</th>
                    <th className="p-2 text-center">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800 text-[11px]">
                  {resultsData.windows.map((w, idx) => (
                    <tr
                      key={idx}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-800/40 cursor-pointer ${
                        idx === inspectedWindowIdx ? 'bg-slate-50 dark:bg-slate-800/70 font-semibold' : ''
                      }`}
                      onClick={() => setInspectedWindowIdx(idx)}
                    >
                      <td className="p-2 font-mono">#{idx + 1}</td>
                      <td className="p-2">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] ${
                            w.verdict === 'KNOWN'
                              ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300'
                              : 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300'
                          }`}
                        >
                          {w.verdict}
                        </span>
                      </td>
                      <td className="p-2">{w.closest_profile}</td>
                      <td className="p-2 text-right font-mono">{(w.top_prob * 100).toFixed(1)}%</td>
                      <td className="p-2 font-mono text-gray-500">{((w.probs?.AmazonEcho || 0) * 100).toFixed(0)}%</td>
                      <td className="p-2 font-mono text-gray-500">{((w.probs?.BelkinWemoMotionSensor || 0) * 100).toFixed(0)}%</td>
                      <td className="p-2 font-mono text-gray-500">{((w.probs?.PhilipsHue || 0) * 100).toFixed(0)}%</td>
                      <td className="p-2 font-mono text-gray-500">{((w.probs?.SamsungCamera || 0) * 100).toFixed(0)}%</td>
                      <td className="p-2 font-mono text-gray-500">{((w.probs?.TPLinkSmartPlug || 0) * 100).toFixed(0)}%</td>
                      <td className="p-2 text-center text-slate-500 hover:text-slate-800 font-mono">
                        {idx === inspectedWindowIdx ? '● Viewing' : 'Select'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Inspected Window Details */}
          {inspectedWindow && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900 p-5">
              <div>
                <h4 className="text-xs font-bold text-gray-900 dark:text-white mb-2">
                  Window #{inspectedWindowIdx + 1} Probability Distribution
                </h4>
                <ProbabilityBars probs={inspectedWindow.probs} dominant={inspectedWindow.closest_profile} />
                <div className="mt-4">
                  <h4 className="text-xs font-bold text-gray-900 dark:text-white mb-1.5">
                    128-Packet IAT Timeline
                  </h4>
                  <IatTimelineChart iats={inspectedWindow.iats} height={70} />
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-gray-900 dark:text-white mb-2">
                  Window #{inspectedWindowIdx + 1} Statistical Features (13 moments)
                </h4>
                <FeaturesTable features={inspectedWindow.features} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
