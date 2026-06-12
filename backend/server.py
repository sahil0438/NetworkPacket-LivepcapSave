# server.py

# IMPORTANT: Apply monkey patching as early as possible for Eventlet/Waitress.
import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, send_file, after_this_request
from flask_sock import Sock
from flask_cors import CORS
# Scapy imports needed in server.py
from scapy.all import sniff, IP, TCP, UDP, ICMP, Ether, Dot11, ARP, Raw, rdpcap, wrpcap, IPv6
from scapy.layers.inet6 import _ICMPv6 as ICMPv6
from scapy.layers.sctp import SCTP
from scapy.layers.dot11 import Dot11Elt

import json
import time
import threading
import uuid
import os
import tempfile
from werkzeug.utils import secure_filename
import logging
import queue # Import Python's built-in queue module, eventlet will monkey-patch it
import simple_websocket.errors # Import for specific exception

# Import the new live PCAP manager module
import live_pcap_manager

# Configure basic logging for visibility
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s (%(name)s): %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app) # Enable CORS for all routes
sock = Sock(app)

# IMPORTANT: Update this with the exact interface name Scapy recognizes on your system
# Use 'getmac /v' on Windows or 'ip a' on Linux/macOS to find the correct name.
# Reverting to "Wi-Fi" as it was the original. Please verify this matches your active interface.
INTERFACE_TO_SNIFF = "Ethernet" # <-- VERIFY THIS NAME!

UPLOAD_FOLDER = 'uploads' # For temporary PCAP uploads for analysis
ALLOWED_EXTENSIONS = {'pcap', 'cap', 'pcapng'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Created upload directory: {UPLOAD_FOLDER}")


# Global variables for sniffing state
sniff_active = False
sniff_thread = None
# Change: Store dict of {ws_object: queue_object}
connected_websockets = {} # Stores active WebSocket connections and their associated queues

# --- Utility Function ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Packet Parsing Logic ---
def parse_packet(packet):
    timestamp = time.time()
    protocol = "N/A"
    length = len(packet)
    info = ""
    source_ip = "N/A"
    dest_ip = "N/A"
    source_port = "N/A"
    dest_port = "N/A"

    IPV6_NEXT_HEADER_MAP = {
        0: "Hop-by-Hop Options", 1: "ICMPv4", 2: "IGMPv4", 6: "TCP", 17: "UDP",
        43: "Routing Header", 44: "Fragment Header", 50: "ESP", 51: "AH",
        58: "ICMPv6", 59: "No Next Header", 60: "Destination Options",
        132: "SCTP",
    }

    if packet.haslayer(IP):
        source_ip = packet[IP].src
        dest_ip = packet[IP].dst
        if packet.haslayer(TCP):
            protocol = "TCP"
            source_port = packet[TCP].sport
            dest_port = packet[TCP].dport
            info = f"{source_ip}:{source_port} -> {dest_ip}:{dest_port} TCP Flags: {packet[TCP].flags}"
        elif packet.haslayer(UDP):
            protocol = "UDP"
            source_port = packet[UDP].sport
            dest_port = packet[UDP].dport
            info = f"{source_ip}:{source_port} -> {dest_ip}:{dest_port} UDP"
        elif packet.haslayer(ICMP):
            protocol = "ICMPv4"
            info = f"{source_ip} -> {dest_ip} ICMP Type: {packet[ICMP].type}"
        else:
            protocol = packet[IP].proto
            info = f"{source_ip} -> {dest_ip} IP Protocol: {protocol}"
    elif packet.haslayer(IPv6):
        source_ip = packet[IPv6].src
        dest_ip = packet[IPv6].dst
        if packet.haslayer(TCP):
            protocol = "TCPv6"
            source_port = packet[TCP].sport
            dest_port = packet[TCP].dport
            info = f"{source_ip}:{source_port} -> {dest_ip}:{dest_port} TCPv6 Flags: {packet[TCP].flags}"
        elif packet.haslayer(UDP):
            protocol = "UDPv6"
            source_port = packet[UDP].sport
            dest_port = packet[UDP].dport
            info = f"{source_ip}:{source_port} -> {dest_ip}:{dest_port} UDPv6"
        elif packet.haslayer(ICMPv6):
            protocol = "ICMPv6"
            info = f"{source_ip} -> {dest_ip} ICMPv6 Type: {packet[ICMPv6].type}"
        elif packet.haslayer(SCTP):
            protocol = "SCTPv6"
            source_port = packet[SCTP].sport
            dest_port = packet[SCTP].dport
            info = f"{source_ip}:{source_port} -> {dest_ip}:{dest_port} SCTPv6"
        else:
            nh_value = packet[IPv6].nh
            protocol = IPV6_NEXT_HEADER_MAP.get(nh_value, f"IPv6-NH:{nh_value}")
            info = f"{source_ip} -> {dest_ip} IPv6 Protocol: {protocol}"
    elif packet.haslayer(ARP):
        protocol = "ARP"
        info = f"ARP: {packet[ARP].psrc} -> {packet[ARP].pdst}"
        source_ip = packet[ARP].psrc
        dest_ip = packet[ARP].pdst
    elif packet.haslayer(Ether):
        protocol = "Ethernet"
        info = f"{packet.summary()}"
    elif packet.haslayer(Dot11):
        protocol = "Dot11"
        info = packet.summary()
        if Dot11Elt in packet and packet[Dot11Elt].ID == 0:
            info += f" SSID: {packet[Dot11Elt].info.decode(errors='ignore')}"
    elif packet.haslayer(Raw):
        protocol = "Raw"
        info = "Raw Data"
    else:
        info = packet.summary()
        if "TCP" in info: protocol = "TCP"
        elif "UDP" in info: protocol = "UDP"
        elif "ICMP" in info: protocol = "ICMP"
        elif "IP" in info: protocol = "IP"
        elif "ARP" in info: protocol = "ARP"
        elif "IPv6" in info: protocol = "IPv6"
        elif "DNS" in info: protocol = "DNS"
        elif "SCTP" in info: protocol = "SCTP"
        else: protocol = packet.name

    packet_data = {
        "id": str(uuid.uuid4()), "timestamp": timestamp, "protocol": str(protocol),
        "length": length, "sourceIP": str(source_ip), "destIP": str(dest_ip),
        "sourcePort": str(source_port), "destPort": str(dest_port),
        "info": str(info), "data": packet.build().hex()
    }
    return packet_data

# --- Live Sniffing Logic ---
def sniff_packets_thread(interface, stop_event, client_queues): # client_queues is now the connected_websockets dict
    global sniff_active
    logger.info(f"Starting live sniffing thread on interface: {interface}")

    sniff_active = True
    stop_event.clear()

    def packet_callback(packet):
        logger.debug("Packet received by packet_callback!") # <--- ADDED LOG
        parsed_packet = parse_packet(packet)
        message = {"type": "packet", "data": parsed_packet}
        json_message = json.dumps(message) # Dump once to JSON

        # Put message into each connected client's queue
        # Iterate over values (queues) to allow deletion of ws from dict in main thread
        for ws_queue in list(client_queues.values()):
            try:
                # Put with a timeout to prevent blocking the sniffing thread if a queue is full
                ws_queue.put_nowait(json_message)
            except queue.Full:
                logger.warning("Client queue is full, dropping packet for this client.")
            except Exception as e:
                # This exception might indicate an issue with the queue itself or its associated ws
                logger.error(f"Error putting packet into client queue: {e}", exc_info=True)

        # Live save to PCAP file using the manager
        if live_pcap_manager.get_live_save_status():
            try:
                live_pcap_manager.write_packet_to_live_pcap(packet)
            except Exception as e:
                logger.critical(f"Error writing live PCAP: {e}", exc_info=True)

    try:
        while not stop_event.is_set():
            logger.debug(f"Sniffing iteration loop: Checking stop_event. Sniff active: {sniff_active}")
            try:
                sniff(iface=interface, prn=packet_callback, store=0, timeout=1)
                logger.debug("Scapy sniff call returned (after 1s timeout or packets processed).")
            except Exception as e:
                logger.critical(f"Scapy sniff function encountered an error on interface {interface}: {e}", exc_info=True)
                stop_event.set()
                logger.info("Setting stop_event due to Scapy sniff error.")
                break

            if stop_event.is_set():
                logger.debug("Stop event detected during sniffing loop. Exiting loop.")
                break

    except Exception as e:
        logger.critical(f"An unhandled error occurred in sniff_packets_thread: {e}", exc_info=True)
        for ws_queue in list(client_queues.values()):
            try:
                ws_queue.put_nowait(json.dumps({"type": "error", "message": f"Server-side sniffing error: {e}"}))
            except Exception as inner_e:
                logger.error(f"Error putting error message into client queue: {inner_e}")

    finally:
        logger.info(f"Final cleanup in sniff_packets_thread. Stopping on interface: {interface}.")
        sniff_active = False
        stop_event.clear()
        live_pcap_manager.close_live_pcap_writer()
        logger.info("Live PCAP writer closed during thread cleanup.")


@app.route('/start', methods=['POST'])
def start_capture_route():
    global sniff_active, sniff_thread
    logger.debug(f"start_capture_route received. Current sniff_active state: {sniff_active}")

    request_data = request.json
    enable_live_save = request_data.get('enableLiveSave', False)
    max_size_mb = request_data.get('maxFileSize', 5)
    filename_prefix = request_data.get('filenamePrefix', "live_capture")

    if not sniff_active:
        sniff_active = True
        live_pcap_manager.set_live_save_active(enable_live_save)

        if live_pcap_manager.get_live_save_status():
            try:
                live_pcap_manager.initialize_live_pcap_writer(filename_prefix, max_size_mb)
                logger.info(f"Live PCAP saving ENABLED. Max size: {max_size_mb}MB, Prefix: {filename_prefix}")
            except Exception as e:
                sniff_active = False
                logger.error(f"Failed to initialize live PCAP saving: {e}")
                return jsonify({"status": "Failed to start sniffing: PCAP save error", "error": str(e)}), 500

        stop_event = threading.Event()
        sniff_thread = threading.Thread(target=sniff_packets_thread,
                                         args=(INTERFACE_TO_SNIFF, stop_event, connected_websockets))
        sniff_thread.stop_event = stop_event
        sniff_thread.daemon = True
        sniff_thread.start()
        logger.info("Capture start requested. Sniffing thread started.")
        return jsonify({"status": "Sniffing started"}), 200

    logger.warning("Capture already active, ignoring start request.")
    return jsonify({"status": "Sniffing already active"}), 400

@app.route('/stop', methods=['POST'])
def stop_capture_route():
    global sniff_active, sniff_thread
    if sniff_active or (sniff_thread and sniff_thread.is_alive()):
        logger.info("Attempting to stop capture.")
        if sniff_thread and sniff_thread.is_alive():
            sniff_active = False
            sniff_thread.stop_event.set()
            sniff_thread.join(timeout=10)
            if sniff_thread.is_alive():
                logger.warning("Sniffing thread did not terminate gracefully within timeout.")
            sniff_thread = None
            live_pcap_manager.close_live_pcap_writer()
            logger.info("Capture stopped successfully.")
            return jsonify({"status": "Sniffing stopped"}), 200
        else:
            sniff_active = False
            live_pcap_manager.close_live_pcap_writer()
            logger.warning("Sniffing thread found inactive, but capture was marked active. Resetting state.")
            return jsonify({"status": "Sniffing already stopped (resetting state)"}), 200
    else:
        logger.warning("Sniffing not active, ignoring stop request (already stopped).")
        return jsonify({"status": "Sniffing already stopped"}), 200

# --- WebSocket Handling ---
@sock.route('/ws')
def websocket_connection(ws):
    logger.debug("Entered websocket_connection function.")
    logger.info("WebSocket client connected")
    # Create a new queue for this specific WebSocket client
    client_queue = queue.Queue(maxsize=1000) # Limit queue size to prevent memory issues
    connected_websockets[ws] = client_queue # Add to our dict

    try:
        # Add a small initial delay here to let the client fully establish
        # and for the browser to send any initial handshake completion.
        eventlet.sleep(0.1) # Added small initial sleep

        while True:
            # Prioritize sending queued packets
            while not client_queue.empty(): # Keep sending until queue is empty
                try:
                    message_to_send = client_queue.get_nowait() # Non-blocking get
                    ws.send(message_to_send)
                    logger.debug(f"Successfully sent packet to WebSocket client. Queue size: {client_queue.qsize()}")
                except queue.Empty:
                    break # Should not happen with not client_queue.empty() but good practice
                except Exception as e:
                    logger.error(f"Error sending queued packet: {e}", exc_info=True)
                    # If sending fails, assume WS is broken and force close the connection
                    raise simple_websocket.errors.ConnectionClosed(code=1006, reason="Send error occurred")

            # Then, check for any incoming messages from the client (with a moderate timeout)
            # This allows the loop to yield control and detect client disconnects,
            # but isn't so short that it causes false disconnects.
            try:
                message_from_client = ws.receive(timeout=1) # Moderate timeout (1 second)
                if message_from_client is None: # Client disconnected
                    logger.info("WebSocket receive indicated client disconnected (None message).")
                    break
                logger.debug(f"Received unhandled message from WebSocket client: {message_from_client}")
            except simple_websocket.errors.ConnectionClosed:
                logger.info("WebSocket connection closed by client during receive.")
                break
            except eventlet.timeout.Timeout:
                # This is expected if no client message comes within the timeout.
                # We just continue the loop to check the queue again.
                pass
            except Exception as e:
                logger.error(f"Error during WebSocket receive from client: {e}", exc_info=True)
                break # Break on other errors

            # Important: Yield control to Eventlet hub to allow other greenlets to run
            # This prevents this greenlet from hogging CPU if there are no packets to send
            # and no incoming messages from the client.
            eventlet.sleep(0) # Yield control immediately

    except simple_websocket.errors.ConnectionClosed as e:
        logger.info(f"WebSocket connection closed by client (outer loop): {e.code}, {e.reason}")
    except Exception as e:
        logger.error(f"WebSocket error in connection handler: {e}", exc_info=True)
    finally:
        # Remove this WebSocket from the dictionary
        if ws in connected_websockets:
            del connected_websockets[ws]
            logger.info("WebSocket client disconnected and removed from tracking.")

# --- PCAP File Upload and Analysis Endpoint ---
@app.route('/upload_pcap', methods=['POST'])
def upload_pcap():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + "_" + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        try:
            file.save(filepath)
            logger.info(f"Received PCAP file: {filepath}")
            packets_from_pcap = rdpcap(filepath)
            logger.info(f"Processing {len(packets_from_pcap)} packets from PCAP...")

            for i, packet in enumerate(packets_from_pcap):
                # For PCAP upload, also use the queues
                if not connected_websockets:
                    logger.warning("No WebSocket clients connected for PCAP send.")
                    break
                for ws_queue in list(connected_websockets.values()):
                    try:
                        parsed_packet = parse_packet(packet)
                        message = {"type": "packet", "data": parsed_packet}
                        ws_queue.put_nowait(json.dumps(message))
                    except queue.Full:
                        logger.warning("Client queue is full during PCAP upload, dropping packet.")
                    except Exception as e:
                        logger.error(f"Error putting PCAP packet into queue: {e}", exc_info=True)


                if i % 100 == 0 and len(packets_from_pcap) > 1000:
                    eventlet.sleep(0.01) # Use eventlet.sleep for green thread compatibility

            logger.info("Finished processing PCAP.")
            return jsonify({"status": "PCAP file processed and packets sent"}), 200

        except Exception as e:
            logger.error(f"Error processing PCAP file: {e}", exc_info=True)
            return jsonify({"error": f"Failed to process PCAP file: {e}"}), 500
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")

    return jsonify({"error": "Invalid file type"}), 400

# --- Server-Side PCAP Export Endpoint ---
@app.route('/export_pcap', methods=['POST'])
def export_pcap_data():
    try:
        packets_json_data = request.json
        if not packets_json_data:
            return jsonify({"error": "No packet data provided"}), 400

        scapy_packets = []
        for p_json in packets_json_data:
            try:
                if 'data' in p_json and p_json['data']:
                    raw_bytes = bytes.fromhex(p_json['data'])
                    try:
                        scapy_packet = Ether(raw_bytes)
                    except Exception:
                        scapy_packet = Raw(raw_bytes)
                    scapy_packets.append(scapy_packet)
                else:
                    logger.debug(f"Skipping packet with no 'data' field for PCAP export: {p_json.get('id', 'N/A')}")
            except Exception as e:
                logger.error(f"Could not reconstruct Scapy packet from JSON for export (ID: {p_json.get('id', 'N/A')}): {e}", exc_info=True)

        if not scapy_packets:
            return jsonify({"error": "No valid packets could be reconstructed for PCAP export"}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pcap") as tmp_file:
            temp_filepath = tmp_file.name
            wrpcap(temp_filepath, scapy_packets)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(temp_filepath)
                logger.info(f"Cleaned up temporary PCAP file: {temp_filepath}")
            except Exception as e:
                logger.error(f"Error removing temporary file {temp_filepath}: {e}", exc_info=True)
            return response

        return send_file(
            temp_filepath,
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=f"exported_packets_{int(time.time())}.pcap"
        )

    except Exception as e:
        logger.error(f"Error during server-side PCAP export: {e}", exc_info=True)
        return jsonify({"error": f"Server-side PCAP export failed: {e}"}), 500


# Error handler for 404 (Not Found)
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found'}), 404

if __name__ == '__main__':
    logger.info("Initializing Flask app and Eventlet server.")
    sniff_active = False
    sniff_thread = None

    live_pcap_manager.set_live_save_active(False)
    live_pcap_manager.close_live_pcap_writer()

    logger.info("Running on Windows: Using Eventlet WSGI server directly for WebSocket support.")
    from eventlet import wsgi
    wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)