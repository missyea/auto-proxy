from flask import Flask, request, jsonify
from flask_cors import CORS

from config import VM_TYPE, FLASK_HOST, FLASK_PORT, LOG_LEVEL
from vm_manager import VMwareManager, HyperVManager

import logging

logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)


def get_vm_manager():
    if VM_TYPE == "VMware Workstation Pro":
        return VMwareManager()
    elif VM_TYPE == "Hyper-V":
        return HyperVManager()
    else:
        raise ValueError(f"Unsupported VM type: {VM_TYPE}")


vm_manager = get_vm_manager()

app = Flask(__name__)
CORS(app)


@app.route("/set_vm", methods=["POST"])
def set_vm():
    received_ip = request.form.get("ip")
    last_ip = request.form.get("last_ip")
    host = request.form.get("host")

    if not received_ip:
        logger.warning("No IP address provided in request")
        return jsonify({"error": "IP address is required"}), 422

    try:
        vm_manager.clone_vm(received_ip, last_ip=last_ip)
        if host:
            vm_manager.hyperv.resolve_dns(host)
        return jsonify({"status": 200})
    except Exception as e:
        logger.error(f"Failed to create VM: {str(e)}")
        return jsonify({"error": "Failed to create VM"}), 500


@app.route("/stop_vm", methods=["POST"])
def stop_vm():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("No IP address provided in request")
        return jsonify({"error": "IP address is required"}), 422

    vm_manager.stop_vm(received_ip)
    return jsonify({"status": 200})


@app.route("/reset_vm", methods=["POST"])
def reset_vm():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("No IP address provided in request")
        return jsonify({"error": "IP address is required"}), 422

    try:
        vm_manager.reset_vm(received_ip)
        return jsonify({"status": 200})
    except Exception as e:
        logger.error(f"Failed to reset VM: {str(e)}")
        return jsonify({"error": "Failed to reset VM"}), 500


@app.route("/delete_vm", methods=["POST"])
def delete_vm():
    received_ip = request.form.get("ip")
    if not received_ip:
        logger.warning("No IP address provided in request")
        return jsonify({"error": "IP address is required"}), 422

    vm_manager.delete_vm(received_ip)
    return jsonify({"status": 200})


@app.route("/get_ip", methods=["GET"])
def get_ip():
    client_ip = request.remote_addr
    vm_name = vm_manager.get_running_vm_name(client_ip)

    if vm_name:
        return jsonify({"ip": vm_name})
    else:
        return jsonify({"error": "No running VM found for this IP"}), 404


@app.route("/get_vm_ip", methods=["GET"])
def get_vm_ip():
    client_name = request.args.get("ip")
    if not client_name:
        logger.warning("No name provided in request")
        return jsonify({"error": "VM name is required"}), 422

    vm_ip = vm_manager.get_running_vm_ip(client_name)
    if vm_ip:
        return jsonify({"ip": vm_ip})
    else:
        return jsonify({"error": "No running VM found with this name"}), 404


@app.route("/get_vm_list", methods=["GET"])
def get_vm_list():
    vm_list = vm_manager.get_vm_list()
    return jsonify({"vm_list": vm_list})


if __name__ == "__main__":
    logger.info(f"Starting VM Management server with {VM_TYPE}")
    app.run(host=FLASK_HOST, port=FLASK_PORT)
