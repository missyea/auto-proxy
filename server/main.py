from flask import Flask, request, jsonify
from flask_cors import CORS

from config import VM_TYPE, FLASK_HOST, FLASK_PORT, LOG_LEVEL
from vm_manager import VMwareManager, ParallelsManager

import logging

logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)


def get_vm_manager():
    if VM_TYPE == "VMware Workstation Pro":
        return VMwareManager()
    elif VM_TYPE == "Parallels Desktop":
        return ParallelsManager()
    else:
        raise ValueError(f"Unsupported VM type: {VM_TYPE}")


vm_manager = get_vm_manager()

app = Flask(__name__)
CORS(app)


@app.route("/set_vm", methods=["POST"])
def set_vm():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("Error parsing JSON data: No valid IP address received")
        return "", 422

    vm_manager.clone_vm(received_ip)
    return jsonify({"status": 200})


@app.route("/stop_vm", methods=["POST"])
def stop_vm():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("Error parsing JSON data: No valid IP address received")
        return "", 422

    vm_manager.stop_vm(received_ip)
    return jsonify({"status": 200})


@app.route("/reset_vm", methods=["POST"])
def reset_vm_endpoint():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("Error parsing JSON data: No valid IP address received")
        return "", 422

    vm_manager.reset_vm(received_ip)
    return jsonify({"status": 200})


@app.route("/delete_vm", methods=["POST"])
def delete_vm_endpoint():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("Error parsing JSON data: No valid IP address received")
        return "", 422

    vm_manager.delete_vm(received_ip)
    return jsonify({"status": 200})


@app.route("/get_ip", methods=["GET"])
def get_ip():
    client_ip = request.remote_addr
    vm_name = vm_manager.get_running_vm_name(client_ip)

    if vm_name:
        return jsonify({"ip": vm_name})
    else:
        return jsonify({"error": "No running VM found matching the IP"}), 404


@app.route("/get_vm_ip", methods=["GET"])
def get_vm_ip():
    client_name = request.args.get("ip")
    vm_ip = vm_manager.get_running_vm_ip(client_name)

    if vm_ip:
        return jsonify({"ip": vm_ip})
    else:
        return jsonify({"error": "No running VM found matching the NAME"}), 404


@app.route("/get_vm_list", methods=["GET"])
def get_vm_list():
    vm_list = vm_manager.get_vm_list()

    return jsonify({"vm_list": vm_list})


if __name__ == "__main__":
    logger.info(f"Starting VM Management server with {VM_TYPE}")
    app.run(host=FLASK_HOST, port=FLASK_PORT)
