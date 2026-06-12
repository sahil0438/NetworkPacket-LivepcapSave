import React from 'react';

const ControlPanel = ({
  isCapturing,
  packetCount,
  packets, // All packets (for export)
  filter,
  setFilter,
  startCapture,
  stopCapture,
  clearPackets,
  exportPackets,
  filteredPackets, // Packets after applying filter
  wsRef, // WebSocket ref (though not directly used in UI, passed for context)
  isImporting,
  importPcap,
  isExporting,
  // Props for Live PCAP Save
  enableLiveSave,
  setEnableLiveSave,
  maxFileSize,
  setMaxFileSize,
  filenamePrefix,
  setFilenamePrefix,
}) => {
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      importPcap(file);
    }
  };

  return (
    <div className="bg-gray-800 p-4 rounded-lg shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        {/* Capture Control Buttons */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => startCapture(enableLiveSave, maxFileSize, filenamePrefix)} // Corrected onClick handler
            disabled={isCapturing}
            className={`px-6 py-3 rounded-md font-semibold transition duration-200 shadow-md
              ${isCapturing ? 'bg-red-600 hover:bg-red-700 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {isCapturing ? 'Capturing...' : 'Start Capture'}
          </button>
          <button
            onClick={stopCapture}
            disabled={!isCapturing}
            className={`px-6 py-3 rounded-md font-semibold transition duration-200 shadow-md
              ${!isCapturing ? 'bg-gray-600 hover:bg-gray-700 cursor-not-allowed' : 'bg-yellow-600 hover:bg-yellow-700'}`}
          >
            Stop Capture
          </button>
          <button
            onClick={clearPackets}
            disabled={packets.length === 0 && !isCapturing}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-md font-semibold transition duration-200 shadow-md"
          >
            Clear Packets
          </button>
        </div>

        {/* Packet Count and Filter */}
        <div className="flex items-center gap-4">
          <span className="text-lg font-medium">Packets: {packetCount}</span>
          <input
            type="text"
            placeholder="Filter packets..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-4 py-2 rounded-md bg-gray-700 border border-gray-600 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* PCAP Import/Export and Live Save Options */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Import PCAP */}
        <div className="flex items-center gap-4">
          <label htmlFor="pcap-upload" className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded-md font-semibold cursor-pointer transition duration-200 shadow-md">
            {isImporting ? 'Importing...' : 'Import PCAP'}
            <input
              id="pcap-upload"
              type="file"
              accept=".pcap,.cap,.pcapng"
              onChange={handleFileChange}
              disabled={isImporting || isCapturing}
              className="hidden"
            />
          </label>
          {/* Export PCAP */}
          <button
            onClick={exportPackets}
            disabled={packets.length === 0 || isExporting || isCapturing}
            className={`px-6 py-3 rounded-md font-semibold transition duration-200 shadow-md
              ${(packets.length === 0 || isExporting || isCapturing) ? 'bg-gray-600 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
          >
            {isExporting ? 'Exporting...' : 'Export PCAP'}
          </button>
        </div>

        {/* Live Save Options */}
        <div className="flex items-center gap-4 text-sm">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={enableLiveSave}
              onChange={(e) => setEnableLiveSave(e.target.checked)}
              disabled={isCapturing}
              className="form-checkbox h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
            />
            <span>Enable Live Save</span>
          </label>
          <input
            type="number"
            placeholder="Max Size (MB)"
            value={maxFileSize}
            onChange={(e) => setMaxFileSize(Number(e.target.value))}
            disabled={isCapturing || !enableLiveSave}
            className="w-28 px-3 py-2 rounded-md bg-gray-700 border border-gray-600 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            min="1"
          />
          <input
            type="text"
            placeholder="Filename Prefix"
            value={filenamePrefix}
            onChange={(e) => setFilenamePrefix(e.target.value)}
            disabled={isCapturing || !enableLiveSave}
            className="w-40 px-3 py-2 rounded-md bg-gray-700 border border-gray-600 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;