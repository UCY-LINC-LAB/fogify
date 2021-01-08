import os
import time
import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import Mock

import yaml

from ..FogifySDK import FogifySDK, ExceptionFogifySDK


class InitializationTest(unittest.TestCase):
    url = "controller:5000"
    file = os.path.dirname(os.path.abspath(__file__)) + "/docker-compose.yaml"

    def setUp(self):
        self.fogify = FogifySDK(self.url, self.file)

    def tearDown(self):
        del self.fogify


class TestInitDockerCompose(InitializationTest):

    def test_init_for_simple_compose(self):
        self.assertListEqual(self.fogify.networks, [])
        self.assertListEqual(self.fogify.nodes, [])
        self.assertListEqual(self.fogify.topology, [])
        self.assertListEqual(self.fogify.services, ['moc-service'])
        self.assertIsNotNone(self.fogify.docker_compose)
        self.assertDictEqual(self.fogify.docker_swarm_rep,
                             {'version': '3.7', 'services': {'moc-service': {'image': 'busybox'}}})


class TestModelFunctions(InitializationTest):

    def test_node_model(self):
        self.fogify.add_node('test', 2, 1400, "2G")
        self.assertListEqual(self.fogify.nodes, [
            dict(
                name='test',
                capabilities=dict(
                    processor=dict(
                        cores=2,
                        clock_speed=1400),
                    memory="2G",
                    disk=""
                )

            )
        ])
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_node('test', 2, 1400, "2G")

    def test_network_model(self):
        network_inputs = {
            'test-net-bidirectional': dict(bandwidth='10Mbps', latency=dict(delay='20ms')),
            'test-net': [
                dict(bandwidth='10Mbps', latency=dict(delay='20ms')),
                dict(bandwidth='5Mbps', latency=dict(delay='5ms'))
            ]
        }
        self.fogify.add_bidirectional_network(
            name='test-net-bidirectional',
            bidirectional=network_inputs['test-net-bidirectional']
        )

        self.assertListEqual(self.fogify.networks, [
            dict(
                name='test-net-bidirectional',
                bidirectional=network_inputs['test-net-bidirectional'],
                capacity=None
            )
        ])

        self.fogify.add_network(
            name='test-net',
            uplink=network_inputs['test-net'][0],
            downlink=network_inputs['test-net'][1]
        )

        self.assertListEqual(self.fogify.networks, [
            dict(
                name='test-net-bidirectional',
                bidirectional=network_inputs['test-net-bidirectional'],
                capacity=None
            ),
            dict(
                name='test-net',
                uplink=network_inputs['test-net'][0],
                downlink=network_inputs['test-net'][1],
                capacity=None
            )
        ])

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_bidirectional_network(
                'test-net-bidirectional',
                network_inputs['test-net-bidirectional']
            )

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_network(
                'test-net',
                network_inputs['test-net'][0],
                network_inputs['test-net'][1]
            )

        self.fogify.add_link(
            'test-net',
            'from-node',
            'to-node',
            properties=network_inputs['test-net'][0]
        )
        net = None
        for i in self.fogify.networks:
            if i['name'] == 'test-net':
                net = i
                break

        self.assertListEqual(
            net['links'],
            [
                dict(
                    from_node='from-node',
                    to_node='to-node',
                    bidirectional=True,
                    properties=network_inputs['test-net'][0]
                )
            ]
        )

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_link(
                'does-not-exist-network',
                'from-node',
                'to-node',
                properties=network_inputs['test-net'][0]
            )

    def test_topology_model(self):
        self.tearDown()
        self.setUp()

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_topology_node(
                'test',
                'service',
                'device',
                ['test-network'],
                1
            )

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_topology_node(
                'moc-service',
                'moc-service',
                'device',
                ['test-network'],
                1
            )

        self.fogify.add_node('device', 2, 1400, "2G")

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_topology_node(
                'moc-service',
                'moc-service',
                'device',
                ['test-network'],
                1
            )

        self.fogify.add_bidirectional_network('test-network', dict(bandwidth='10Mbps', latency=dict(delay='20ms')))
        self.fogify.add_topology_node(
            'moc-service',
            'moc-service',
            'device',
            ['test-network'],
            1
        )
        self.assertListEqual(
            self.fogify.topology,
            [
                {
                    'label': 'moc-service',
                    'service': 'moc-service',
                    'node': 'device',
                    'networks': ['test-network'],
                    'replicas': 1
                }
            ]
        )
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.add_topology_node(
                'moc-service',
                'moc-service',
                'device',
                ['test-network'],
                1
            )
        self.fogify.add_topology_node(
            'moc-service-2',
            'moc-service',
            'device',
            ['test-network'],
            1
        )


class TestModelTranslation(InitializationTest):
    file = os.path.dirname(os.path.abspath(__file__)) + "/existing-docker-compose.yaml"

    def test_generated_file(self):
        file = self.fogify.upload_file()
        obj1 = yaml.load(file, Loader=yaml.FullLoader)
        file.close()
        file2 = open(self.file, "r")
        obj2 = yaml.load(file2, Loader=yaml.FullLoader)
        file2.close()
        self.assertDictEqual(obj1, obj2)

        with self.assertRaises(FileNotFoundError):
            open("fogified-docker-compose.yaml", "rb").close()
        self.fogify.upload_file(False)
        open("fogified-docker-compose.yaml", "rb").close()
        os.remove("fogified-docker-compose.yaml")


# request('get', url, params=params, **kwargs)

class TestAPIs(InitializationTest):
    url = "controller:5000"
    file = os.path.dirname(os.path.abspath(__file__)) + "/docker-compose.yaml"

    @mock.patch('requests.delete')
    def test_delete_metrics(self, mock_delete):
        self.fogify.data = {"data": "exsts"}
        mock_delete.return_value = Mock(ok=True)
        mock_delete.return_value.json.return_value = {"message": "The monitorings are empty now"}
        res = self.fogify.clean_metrics()
        self.assertDictEqual(
            res,
            {"message": "The monitorings are empty now"}
        )
        with self.assertRaises(AttributeError):
            self.fogify.data

    @mock.patch('requests.delete')
    def test_delete_annotations(self, mock_delete):
        mock_delete.return_value = Mock(ok=True)
        mock_delete.return_value.json.return_value = {"message": "Annotations are clear"}
        res = self.fogify.clean_annotations()
        self.assertDictEqual(
            res,
            {"message": "Annotations are clear"}
        )

    @mock.patch('requests.get')
    def test_get_annotations(self, mock_get):
        annotation_object = [
            {
                "timestamp": "",
                "annotation": "START",
                "instance_name": "None",
                "params": ""
            },
            {
                "timestamp": "",
                "annotation": "DEPLOY",
                "instance_name": "None",
                "params": ""
            }
        ]
        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = annotation_object
        self.fogify.get_annotations()
        count_row = self.fogify.annotations.shape[0]
        count_col = self.fogify.annotations.shape[1]
        self.assertEqual(count_row, 2)
        self.assertEqual(count_col, 4)

    @mock.patch('requests.get')
    def test_get_metrics_from(self, mock_get):
        monitoring_object = {
            "service-1.1": [
                {"count": 1,
                 "metric-1": 5,
                 "metric-2": 10,
                 "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", datetime.utcnow().utctimetuple())
                 }
            ],
            "service-2.1": [{
                "count": 1,
                "metric-1": 5,
                "metric-2": 10,
                "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", datetime.utcnow().utctimetuple())
            }]
        }
        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = monitoring_object
        metrics = self.fogify.get_metrics_from("service-2.1")
        count_row = metrics.shape[0]
        count_col = metrics.shape[1]
        self.assertEqual(count_row, 1)
        self.assertEqual(count_col, 3)

        self.assertEqual(len(self.fogify.data), 2)

        metrics = self.fogify.get_metrics_from("service-2.1")
        count_row = metrics.shape[0]
        count_col = metrics.shape[1]
        self.assertEqual(count_row, 1)
        self.assertEqual(count_col, 3)

        monitoring_object = {
            "service-1.1": [
                {"count": 2,
                 "metric-1": 5,
                 "metric-2": 10,
                 "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", datetime.utcnow().utctimetuple())
                 }
            ],
            "service-2.1": [{
                "count": 2,
                "metric-1": 5,
                "metric-2": 10,
                "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", datetime.utcnow().utctimetuple())
            }]
        }
        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = monitoring_object
        metrics = self.fogify.get_metrics_from("service-2.1")
        count_row = metrics.shape[0]
        count_col = metrics.shape[1]
        self.assertEqual(count_row, 2)
        self.assertEqual(count_col, 3)

    @mock.patch('requests.get')
    def test_get_network_packets_from(self, mock_get):
        packets_object = {"res": [
            {
                "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", datetime.utcnow().utctimetuple()),
                "service_id": "service-1.1",
                "src_instance": "service-1.1",
                "dest_instance": "service-1.2",
                "network": "test-network",
                "src_ip": "10.0.0.1",
                "dest_ip": "10.0.0.2",
                "protocol": "TCP",
                "size": 200,
                "count": 10,
                "out": True
            },
            {
                "timestamp": time.strftime("%a, %d %b %Y %H:%M:%S %Z", datetime.utcnow().utctimetuple()),
                "service_id": "service-1.1",
                "src_instance": "service-1.2",
                "dest_instance": "service-1.1",
                "network": "test-network",
                "src_ip": "10.0.0.2",
                "dest_ip": "10.0.0.1",
                "protocol": "TCP",
                "size": 150,
                "count": 10,
                "out": False
            }
        ]}
        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = packets_object
        data = self.fogify.get_network_packets_from("service-1.1")
        count_row = data.shape[0]
        count_col = data.shape[1]
        self.assertEqual(count_row, 2)
        self.assertEqual(count_col, 11)

        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = {}
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.get_network_packets_from("service-1.1")

    @mock.patch('requests.request')
    def test_actions(self, mock_post):
        mock_post.return_value = Mock(ok=True)
        mock_post.return_value.json.return_value = {"message": "ok"}
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.action("non-type", test={})

        self.assertDictEqual(self.fogify.horizontal_scaling_up("service-1.1"), {"message": "ok"})
        self.assertDictEqual(self.fogify.horizontal_scaling_down("service-1.1"), {"message": "ok"})

        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.vertical_scaling("service-1.1")
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.vertical_scaling("service-1.1", cpu="4")
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.vertical_scaling("service-1.1", cpu="+test")
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.vertical_scaling("service-1.1", cpu="+40", memory="2g")
        self.fogify.vertical_scaling("service-1.1", cpu="+40")
        self.assertDictEqual(self.fogify.vertical_scaling("service-1.1", cpu="+40"), {"message": "ok"})
        self.assertDictEqual(self.fogify.vertical_scaling("service-1.1", memory="2g"), {"message": "ok"})

        self.assertDictEqual(self.fogify.update_network("service-1.1", "test-network"), {"message": "ok"})
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.stress("service-1.1")

        self.assertDictEqual(self.fogify.stress("service-1.1", cpu=5), {"message": "ok"})

    @mock.patch('FogifySDK.FogifySDK.undeploy')
    @mock.patch('FogifySDK.FogifySDK.clean_annotations')
    @mock.patch('FogifySDK.FogifySDK.clean_metrics')
    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_deploy(self, mock_get, mock_post, mock_clean_metrics, mock_clean_annotations, mock_undeploy):
        mock_clean_metrics.return_value = Mock(ok=True)
        mock_clean_annotations.return_value = Mock(ok=True)
        mock_undeploy.return_value = Mock(ok=True)
        mock_post.return_value = Mock(ok=True)
        mock_post.return_value.json.return_value = {}
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.deploy()
        mock_post.return_value.json.return_value = {
            "message": "OK",
            "swarm": {
                "services": {
                    "service-1": {
                        "deploy": {
                            "replicas": 1
                        }
                    },
                    "service-2": {
                        "deploy": {
                            "replicas": 1
                        }
                    }
                }
            },
            "networks": {}
        }

        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = {
            "service-1": [
                "service-1"
            ],
            "service-2": [
                "service-2"
            ]
        }
        self.assertDictEqual(self.fogify.deploy(), {
            "message": "The services are deployed ( {'service-1': 1, 'service-2': 1} )"
        })

        mock_get.return_value.json.return_value = {
            "service-1": [
            ],
            "service-2": [
            ]
        }
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.deploy(1)


    @mock.patch('requests.delete')
    @mock.patch('requests.get')
    def test_undeploy(self, mock_get, mock_delete):
        self.tearDown()
        self.setUp()
        mock_delete.return_value = Mock(ok=False)
        mock_delete.return_value.status_code = 500
        mock_delete.return_value.json.return_value = {}
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.undeploy()

        mock_delete.return_value = Mock(ok=True)
        mock_delete.return_value.status_code = 200
        mock_delete.return_value.json.return_value = {"message": "The topology is down."}
        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = {
            "service-1": [
                "service-1"
            ],
            "service-2": [
                "service-2"
            ]
        }
        with self.assertRaises(ExceptionFogifySDK):
            self.fogify.undeploy(1)
        mock_get.return_value = Mock(ok=True)
        mock_get.return_value.json.return_value = {}
        self.assertDictEqual(self.fogify.undeploy(), {
            "message": "The 0 services are undeployed"
        })

if __name__ == '__main__':
    unittest.main()
