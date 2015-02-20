from __future__ import print_function, unicode_literals

"""
The main reason this is not using unittest is that unittest doesn't support parametrized tests.
"""

import json
import time
import requests
import sys
import traceback
import logging

from docker import Client


d = Client()


class EapTest(object):
    """ smoke test suite for EAP """

    def __init__(self, image_id, config_file, logger=None, **kwargs):
        self.image_id = image_id
        self.config_file = config_file
        self.logger = logger
        self.kwargs = kwargs
        with open(config_file, "r") as json_data_file:
            self.config = json.load(json_data_file)

    def _log(self, m, level=logging.INFO):
        """ log using logger, or print to stdout """
        if self.logger:
            self.logger.log(level, m)
        else:
            print(m)

    def setup(self):
        """ this method is called before every test run """
        self._log("creating container from image '%s'" % self.image_id, logging.DEBUG)
        self.container = d.create_container(image=self.image_id, detach=True)
        d.start(container=self.container)

    def teardown(self):
        """ called after every test run """
        if self.container:
            self._log("removing container '%s'" % self.container['Id'], logging.DEBUG)
            d.kill(container=self.container)
            d.remove_container(self.container)
        else:
            self._log("no container to tear down", logging.DEBUG)
        self.container = None

    def run(self):
        """ entry point, run all tests and return results """
        # decorator might be more suitable
        tests = [
            EapTest.test_product_is_listening,
            EapTest.test_log_contanis_start_message,
        ]
        results = {}
        passed = True
        for test in tests:
            test_name = test.__func__.__name__
            self._log("starting test '%s'" % test_name, logging.INFO)
            self.setup()
            try:
                test_result = test(self)
            except Exception as ex:
                results[test_name] = traceback.format_exc()
                passed = False
            else:
                results[test_name] = test_result
                if test_result is False:
                    passed = False
            self._log("test result: '%s'" % results[test_name], logging.INFO)
            self.teardown()
        self._log("did tests pass? '%s'" % passed, logging.INFO)
        return results, passed

    def test_product_is_listening(self):
        result = False
        start_time = time.time()
        ip = d.inspect_container(container=self.container)['NetworkSettings']['IPAddress']
        while time.time() < start_time + self.config['timeout']:
            try:
                response = requests.get('http://' + ip + ':' + str(self.config['port']), timeout = 0.5, stream=False)
            except Exception as ex:
                self._log("exc: %s" % repr(ex))
            else:
                self._log("response code: %d" % response.status_code)
                if response.status_code == 200:
                    result=True
                    break
            time.sleep(1)
        return result

    def test_log_contanis_start_message(self):
        result = False
        start_time = time.time()
        while time.time() < start_time + self.config['timeout']:
            logs = d.attach(container=self.container.get('Id'), stream=False, logs=True)
            self._log("container logs: '%s'" % logs, logging.DEBUG)
            if self.config['ok_log_entry'] in logs:
                result = True
                break
            time.sleep(1)
        return result


def run(config_file, image_id, logger=None, **kwargs):
    e = EapTest(image_id, config_file, logger=None, **kwargs)
    return e.run()

