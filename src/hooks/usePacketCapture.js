import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

const usePacketCapture = () => {
    console.log("USEPACKETCAPTURE: Hook called/re-rendered."); // Diagnostic log

    const [packets, setPackets] = useState([]);
    const [isCapturing, setIsCapturing] = useState(false);
    const [wsConnected, setWsConnected] = useState(false);
    const [alert, setAlert] = useState(null);

    const wsRef = useRef(null); // Ref to hold the WebSocket instance
    const packetsRef = useRef([]); // Ref to hold the latest packets array for onmessage
    
    // Flag to indicate if the component is truly unmounting
    const isUnmounting = useRef(false); 

    // Update packetsRef whenever packets state changes
    useEffect(() => {
        packetsRef.current = packets;
    }, [packets]);

    // This useEffect will now manage the entire WebSocket lifecycle
    // It runs ONLY ONCE on component mount and cleans up ONLY ONCE on unmount
    useEffect(() => {
        console.log("FRONTEND LOG: WebSocket useEffect setup running.");
        isUnmounting.current = false; // Reset flag on new setup

        const establishWebSocketConnection = () => {
            if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
                console.log("FRONTEND LOG: WebSocket already open or connecting. ReadyState:", wsRef.current.readyState);
                setWsConnected(true);
                return;
            }

            console.log("FRONTEND LOG: Attempting to establish NEW WebSocket connection...");
            const ws = new WebSocket(API_BASE_URL.replace('http', 'ws') + '/ws');
            
            ws.onopen = () => {
                console.log('FRONTEND LOG: WebSocket connected');
                setWsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'packet') {
                        setPackets(prevPackets => [...prevPackets, message.data]);
                    } else if (message.type === 'error') {
                        console.error('FRONTEND LOG: WebSocket Error from Server:', message.message);
                        setAlert({ type: 'error', message: message.message });
                    }
                } catch (error) {
                    console.error('FRONTEND LOG: Error parsing WebSocket message:', error, event.data);
                }
            };

            ws.onclose = (event) => {
                console.log('FRONTEND LOG: WebSocket disconnected', event.code, event.reason);
                setWsConnected(false);
                setIsCapturing(false); // Stop capturing state on UI if WS disconnects

                // Reconnect logic: Only attempt to reconnect if it was an unexpected closure
                // AND we are NOT in the process of unmounting (which would mean a new WS is coming).
                if (event.code !== 1000 && event.code !== 1005 && !isUnmounting.current) {
                    console.log('FRONTEND LOG: WebSocket closed unexpectedly. Attempting to reconnect in 2 seconds...');
                    setTimeout(establishWebSocketConnection, 2000); // Use the inner function for reconnect
                } else if (isUnmounting.current) {
                    console.log('FRONTEND LOG: WebSocket closed due to component unmount. Not reconnecting.');
                }
            };

            ws.onerror = (error) => {
                console.error('FRONTEND LOG: WebSocket error:', error);
                setWsConnected(false);
                setIsCapturing(false);
                setAlert({ type: 'error', message: 'WebSocket connection error. Check server logs.' });
            };

            wsRef.current = ws; // Store the new WebSocket instance in the ref
        };

        // Call the function to establish connection when the effect runs
        establishWebSocketConnection();

        // Cleanup function: This runs when the component unmounts OR when HMR triggers a re-run
        return () => {
            console.log("FRONTEND LOG: WebSocket useEffect cleanup running.");
            isUnmounting.current = true; // Set flag to indicate cleanup is in progress

            // ONLY close the WebSocket if it's still the one we created AND it's open
            // This implicitly handles HMR: if a new instance is created, wsRef.current will be different.
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close(1000, "Component unmounted/HMR reload");
                console.log("FRONTEND LOG: WebSocket closed by cleanup.");
            } else {
                console.log("FRONTEND LOG: WS instance not open or already closed during cleanup.");
            }
        };
    }, []); // Empty dependency array: runs once on mount, cleans up once on unmount

    // --- API Call Functions ---
    const startCapture = async (enableLiveSave = false, maxFileSize = 5, filenamePrefix = "live_capture") => {
        console.log("FRONTEND LOG: startCapture function called");
        if (isCapturing) {
            setAlert({ type: 'info', message: 'Capture already active.' });
            return;
        }

        // Ensure WebSocket is connected before trying to start capture
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setAlert({ type: 'error', message: 'WebSocket not connected. Please wait or refresh.' });
            console.error("FRONTEND LOG: Attempted to start capture but WebSocket was not open.");
            return;
        }

        try {
            console.log("FRONTEND LOG: Sending POST to /start with live save options:", { enableLiveSave, maxFileSize, filenamePrefix });
            const response = await axios.post(`${API_BASE_URL}/start`, { enableLiveSave, maxFileSize, filenamePrefix });
            console.log("FRONTEND LOG: Response from /start:", response.data);
            setAlert({ type: 'success', message: response.data.status });
            setIsCapturing(true);
            console.log("FRONTEND LOG: IsCapturing set to true.");

        } catch (error) {
            console.error("FRONTEND LOG: Error starting capture:", error.response ? error.response.data : error.message);
            setAlert({ type: 'error', message: `Failed to start capture: ${error.response ? error.response.data.error || error.response.data.status : error.message}` });
            setIsCapturing(false);
        }
    };

    const stopCapture = async () => {
        console.log("FRONTEND LOG: stopCapture function called");
        if (!isCapturing) {
            setAlert({ type: 'info', message: 'Capture is not active.' });
            return;
        }

        try {
            const response = await axios.post(`${API_BASE_URL}/stop`);
            setAlert({ type: 'success', message: response.data.status });
            setIsCapturing(false);
            console.log("FRONTEND LOG: IsCapturing set to false.");
        } catch (error) {
            console.error("FRONTEND LOG: Error stopping capture:", error.response ? error.response.data : error.message);
            setAlert({ type: 'error', message: `Failed to stop capture: ${error.response ? error.response.data.error || error.response.data.status : error.message}` });
        }
    };

    const clearPackets = () => {
        setPackets([]);
        setAlert({ type: 'info', message: 'Cleared all packets.' });
    };

    const importPcap = async (file) => {
        setAlert(null);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${API_BASE_URL}/upload_pcap`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            console.log('Import PCAP response:', response.data);
            setAlert({ type: 'success', message: 'PCAP imported and packets sent to clients!' });
        } catch (error) {
            console.error('Error importing PCAP:', error.response ? error.response.data : error.message);
            setAlert({ type: 'error', message: `Failed to import PCAP: ${error.response ? error.response.data.error : error.message}` });
        }
    };

    const exportPcap = async () => {
        if (packets.length === 0) {
            setAlert({ type: 'info', message: 'No packets to export.' });
            return;
        }

        try {
            setAlert({ type: 'info', message: 'Preparing PCAP export...' });
            const response = await axios.post(`${API_BASE_URL}/export_pcap`, packetsRef.current, {
                responseType: 'blob',
            });

            const blob = new Blob([response.data], { type: 'application/octet-stream' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `exported_packets_${Date.now()}.pcap`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            setAlert({ type: 'success', message: 'PCAP exported successfully!' });
        } catch (error) {
            console.error('Error exporting PCAP:', error.response ? error.response.data : error.message);
            setAlert({ type: 'error', message: `Failed to export PCAP: ${error.response ? error.response.data.error : error.message}` });
        }
    };

    return {
        packets,
        isCapturing,
        wsConnected,
        alert,
        setAlert,
        startCapture,
        stopCapture,
        clearPackets,
        importPcap,
        exportPcap
    };
};

export default usePacketCapture;
