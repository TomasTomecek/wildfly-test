from docker import Client
import unittest
import json
import time
import requests
import sys
cli = Client(base_url='unix://var/run/docker.sock')

class EapTest():
    config = None
    container = None
    def setup(self, image, config_file):
        # read property files
        with open(config_file) as json_data_file:
            self.config = json.load(json_data_file)
        # start container
        print "creating cointainer " + str(image)
        self.container = cli.create_container(image=image, detach='true')
        cli.start(container=self.container.get('Id'))

    def teardown(self):
        # stop container
        cli.kill(container=self.container.get('Id'))

    def run(self):
        result = True
        result = result and self.test_product_is_listening()
        result = result and self.test_log_contanis_start_message()
        return result

    def test_product_is_listening(self):
        result = False
        start_time = time.time()
        ip = cli.inspect_container(container=self.container)['NetworkSettings']['IPAddress']
        while time.time() < start_time + self.config['timeout']:
            try:
                response = requests.get('http://' + ip + ':' + str(self.config['port']), timeout = 0.5, stream=False)
                if response.status_code == 200:
                    result=True
                    break
                time.sleep(1)
            except:
                #TODO Proper handling
                pass
        print ("JBOSS is listening: " + str(result))
        return result

    def test_log_contanis_start_message(self):
        result = False
        start_time = time.time()
        while time.time() < start_time + self.config['timeout']:
            logs = cli.attach(container=self.container.get('Id'), stream=False,logs=True)
            if self.config['ok_log_entry'] in logs:
                result = True
                break
            time.sleep(1)
        print ("JBOSS logs ok: " + str(result))
        return result
