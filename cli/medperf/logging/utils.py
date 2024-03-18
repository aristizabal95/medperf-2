import csv
import getpass
import grp
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import tarfile

import docker
import pkg_resources
import psutil
import yaml

from medperf import config
from medperf.exceptions import ExecutionError


def get_system_information():
    # Get basic system information
    system_info = {
        "Platform": platform.platform(),
        "Hostname": socket.gethostname(),
        "Processor": platform.processor(),
        "System Version": platform.version(),
        "Python Version": platform.python_version(),
    }
    return system_info


def get_memory_usage():
    # Get memory usage
    memory = psutil.virtual_memory()
    return {
        "Total Memory": memory.total,
        "Available Memory": memory.available,
        "Used Memory": memory.used,
        "Memory Usage Percentage": memory.percent,
    }


def get_disk_usage():
    # Get disk usage
    disk_usage = psutil.disk_usage("/")
    return {
        "Total Disk Space": disk_usage.total,
        "Used Disk Space": disk_usage.used,
        "Free Disk Space": disk_usage.free,
        "Disk Usage Percentage": disk_usage.percent,
    }


def get_user_information():
    # Get user information
    username = getpass.getuser()
    is_sudoers = "sudo" in [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    is_docker_group = "docker" in [
        g.gr_name for g in grp.getgrall() if username in g.gr_mem
    ]
    return {
        "Username": username,
        "Is in Sudoers Group": is_sudoers,
        "Is in Docker Group": is_docker_group,
    }


def get_docker_information():
    try:
        exec_path = shutil.which("docker")
        client = docker.from_env()
        version = client.version()
        info = client.info()
        return {
            "Docker Installed": True,
            "Executable path": exec_path,
            "information": info,
            "Version": version,
        }
    except Exception as e:
        return {"Docker Installed": False, "Error": str(e)}


def get_singularity_information():
    try:
        exec_path = shutil.which("singularity")
        if exec_path is None:
            return {"Singularity installed": False}
        conf_path = "/usr/local/etc/singularity/singularity.conf"
        with open(conf_path, "r") as f:
            conf = f.readlines()
        conf_content = []
        for line in conf:
            if line.startswith("#") or len(line.strip()):
                continue
            conf_content.append(line.strip)
        config_dict = {}
        for line in conf_content:
            key, value = line.split("=")
            key = key.strip().lower()
            value = value.strip()
            if value.isdigit():
                value = int(value)
            config_dict[key] = value
        return {
            "Singularity installed": True,
            "Executable path": exec_path,
            "Configuration": config_dict,
        }
    except Exception as e:
        return {"Singularity installed": False, "Error": str(e)}


def get_configuration_variables():
    config_vars = vars(config)
    config_dict = {}
    for item in dir(config):
        if item.startswith("__"):
            continue
        config_dict[item] = config_vars[item]
    config_dict = filter_var_dict_for_yaml(config_dict)
    return config_dict


def filter_var_dict_for_yaml(unfiltered_dict):
    valid_types = (str, dict, list, int, float)
    filtered_dict = {}
    for key, value in unfiltered_dict.items():
        if not isinstance(value, valid_types) and value is not None:
            try:
                value = str(value)
            except Exception:
                value = "<OBJECT>"
        if isinstance(value, dict):
            value = filter_var_dict_for_yaml(value)
        filtered_dict[key] = value

    return filtered_dict


def get_storage_contents():
    storage_paths = config.storage.copy()
    storage_paths["credentials_folder"] = {
        "base": os.path.dirname(config.creds_folder),
        "name": os.path.basename(config.creds_folder),
    }
    ignore_paths = {"datasets_folder", "predictions_folder", "results_folder"}
    contents = {}

    for pathname, path in storage_paths.items():
        if pathname in ignore_paths:
            contents[pathname] = "<REDACTED>"
            continue
        full_path = os.path.join(path["base"], path["name"])
        p = subprocess.Popen(
            ["ls", "-lR", full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output, _ = p.communicate()
        if p.returncode != 0:
            contents[pathname] = "Could not retrieve tree for storage paths"
        contents[pathname] = output

    return contents


def get_installed_packages():
    installed_packages = {}
    for package in pkg_resources.working_set:
        installed_packages[package.key] = package.version
    return installed_packages


def get_python_environment_information():
    environment_info = {
        "Operating System": platform.system(),
        "Operating System Release": platform.release(),
        "Operating System Version": platform.version(),
        "Python Implementation": platform.python_implementation(),
        "Python Version": platform.python_version(),
        "Python Compiler": platform.python_compiler(),
        "Python Build": platform.python_build(),
        "Machine Architecture": platform.machine(),
        "Processor Type": platform.processor(),
        "Python Executable": shutil.which("python"),
        "Installed Modules": get_installed_packages(),
    }
    return environment_info


def get_gpu_information():
    try:
        gpu_info = {}
        # Get GPU information
        p = subprocess.Popen(
            [
                "nvidia-smi",
                "--query-gpu=index,gpu_name,driver_version,compute_cap,memory.total",
                "--format=csv",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output, _ = p.communicate()
        if p.returncode != 0:
            raise ExecutionError("nvidia-smi not installed/available")
        gpus_data = [row for row in csv.DictReader(output.split("\n"))]
        gpu_info["GPU(s)"] = gpus_data

        # Get CUDA version
        p = subprocess.Popen(
            ["nvidia-smi", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output, _ = p.communicate()
        if p.returncode != 0:
            raise ExecutionError("nvidia-smi not installed/available")
        output = output.split("\n")
        versions = [out.split(":") for out in output if len(out)]
        for key, value in versions:
            gpu_info[key.strip()] = value.strip()

        return gpu_info
    except (subprocess.CalledProcessError, ExecutionError, FileNotFoundError) as e:
        return {"Error": str(e)}


def log_machine_details():
    system_info = {}
    system_info["System Info"] = get_system_information()
    system_info["Memory Usage"] = get_memory_usage()
    system_info["Disk Usage"] = get_disk_usage()
    system_info["User Info"] = get_user_information()
    system_info["Docker Info"] = get_docker_information()
    system_info["Singularity Info"] = get_singularity_information()
    system_info["Medperf Configuration"] = get_configuration_variables()
    system_info["Medperf Storage Contents"] = get_storage_contents()
    system_info["Python Environment"] = get_python_environment_information()
    system_info["GPU(s) Information"] = get_gpu_information()

    debug_dict = {"Machine Details": system_info}

    logging.debug(yaml.dump(debug_dict, default_flow_style=False))

def package_logs():
    files = os.listdir(config.logs_folder)
    logfiles = []
    for file in files:
        is_logfile = re.match(r"medperf\.log(?:\.\d+)?$", file) is not None
        if is_logfile:
            logfiles.append(file)

    package_file = os.path.join(config.logs_folder, config.log_package_file)

    with tarfile.open(package_file, "w:gz") as tar:
        for file in logfiles:
            filepath = os.path.join(config.logs_folder, file)
            tar.add(filepath, arcname=os.path.basename(filepath))