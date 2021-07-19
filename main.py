#!/usr/bin/env python

import dbus
import git
import json
import logging
import requests
import signal
from requests.exceptions import HTTPError
from sys import exit
from time import sleep


def get_config(key):
    with open('config.json', 'r') as file:
        data = json.load(file)
    file.close()
    return data[key]


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


def service_control(service_list, control):
    SYSTEMD_BUSNAME = 'org.freedesktop.systemd1'
    SYSTEMD_PATH = '/org/freedesktop/systemd1'
    SYSTEMD_MANAGER_INTERFACE = 'org.freedesktop.systemd1.Manager'
    bus = dbus.SystemBus()
    systemd_object = bus.get_object(SYSTEMD_BUSNAME, SYSTEMD_PATH)
    systemd_manager = dbus.Interface(systemd_object, SYSTEMD_MANAGER_INTERFACE)
    for service in service_list:
        if control is True:
            print("Starting service: %s" % service)
            systemd_manager.StartUnit(service, 'replace')
        else:
            print("Stopping service: %s" % service)
            systemd_manager.StopUnit(service, 'replace')
        sleep(2)


def git_pull():
    g = git.cmd.Git()
    try:
        g.pull()
    except:
        return


def get_rate():
    global comed_api_url
    loop_seconds = get_config("loop_seconds")
    comed_api_url = get_config("comed_api_url")
    rates = requests.get(comed_api_url)
    rates = rates.json()
    rateset = []
    for i in range(12):
        rateset.append(float(rates[i]['price']))
    return round(mean(rateset), 1)


def cleanup():
    logging.warning("shutting down.")
    exit(0)


def main():
    # catch these termination signals:
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    # initialization:
    state = "new"
    services = get_config("services")

    while True:
        # optional git pull every loop
        if get_config("git_pull"):
            git_pull()

        # allow these to be changes during loop
        rate_limit = get_config("rate_limit")
        loop_seconds = get_config("loop_seconds")

        try:
            current = get_rate()
        except HTTPError as http_error:
            print(f'HTTP error occurred: {http_error}')
            sleep(loop_seconds)

        if current > rate_limit:
            # rate is high:
            if state is not False:
                logging.warning("disabling, rate is " + str(current) + " cents per kWh, and limit is " + str(rate_limit))
                service_control(services, False)
                state = False
        else:
            # rate is low:
            if state is not True:
                logging.warning("enabling, rate is " + str(current) + " cents per kWh, and limit is " + str(rate_limit))
                service_control(services, True)
                state = True

        sleep(loop_seconds)


if __name__ == '__main__':
    main()
