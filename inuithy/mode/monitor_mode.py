## MonitorController application main thread
# Author: Zex Li <top_zlynch@yahoo.com>
#
import socket, logging
import logging.config as lconf
import paho.mqtt.client as mqtt
import threading as thrd
from inuithy.util.cmd_helper import *
from inuithy.util.config_manager import *
#from inuithy.common.traffic import *
from inuithy.common.agent_info import *
from inuithy.util.traffic_state import *

lconf.fileConfig(INUITHY_LOGCONFIG)
lg = logging.getLogger('InuithyMonitorController')

class MonitorController:
    """
    Message Flow:
                        heartbeat
        Agent -------------------------> MonitorController
                        command
        Agent <------------------------- MonitorController
                         config
        Agent <------------------------- MonitorController
                        traffic
        Agent <------------------------- MonitorController
                       newcontroller
        Agent <------------------------- MonitorController
                        response
        Agent -------------------------> MonitorController
                         status
        Agent -------------------------> MonitorController
                        unregister
        Agent -------------------------> MonitorController
    """
    __mutex = thrd.Lock()
    __mutex_msg = thrd.Lock()

    @property
    def traffic_state(self): return self.__traffic_state
    @traffic_state.setter
    def traffic_state(self, val): pass

    @property
    def clientid(self): return self.__clientid
    @clientid.setter
    def clientid(self, val): pass

    @property
    def subscriber(self): return self.__subscriber
    @subscriber.setter
    def subscriber(self, val): pass

    @property
    def host(self): return self.__host
    @host.setter
    def host(self, val): pass

    @property
    def storage(self): return self.__storage
    @storage.setter
    def storage(self, val): pass

    @property
    def tcfg(self):
        """Inuithy configure
        """
        return self.__inuithy_cfg
    @tcfg.setter
    def tcfg(self, val): pass

    @property
    def nwcfg(self):
        """Network configure
        """
        return self.__network_cfg
    @nwcfg.setter
    def nwcfg(self, val): pass

    @property
    def trcfg(self):
        """Traffic configure
        """
        return self.__traffic_cfg
    @trcfg.setter
    def trcfg(self, val): pass

    @property
    def available_agents(self): return self.__available_agents
    @available_agents.setter
    def available_agents(self, val): pass

    @property
    def node2host(self): return self.__node2host

    @node2host.setter
    def node2host(self, val): pass
    @property
    def initialized(self): return MonitorController.__initialized

    @initialized.setter
    def initialized(self, val):
        if MonitorController.__mutex.acquire_lock():
            if not MonitorController.__initialized:
                MonitorController.__initialized = True
            MonitorController.__mutex.release()
    
    @property
    def current_nwlayout(self):
        """FORMAT: <networkconfig_path>:<networklayout_name>"""
        return getnwlayoutid(*self.__current_nwlayout)

    @current_nwlayout.setter
    def current_nwlayout(self, val):
        if not isinstance(val, tuple):
            raise TypeError("Tuple expected")
        self.__current_nwlayout = val

    @staticmethod
    def on_connect(client, userdata, rc):
        lg.info(string_write("MQ.Connection client:{} userdata:[{}] rc:{}", client, userdata, rc))
        if 0 != rc:
            lg.info(string_write("MQ.Connection: connection error"))

    @staticmethod
    def on_message(client, userdata, message):
        lg.info(string_write("MQ.Message: userdata:[{}]", userdata))
        lg.info(string_write("MQ.Message: message "+INUITHY_MQTTMSGFMT, 
            message.dup, message.info, message.mid, message.payload, 
            message.qos, message.retain, message.state, message.timestamp,
            message.topic))
        try:
            userdata.topic_routes[message.topic](message)
        except Exception as ex:
            lg.error(string_write("Exception on MQ message dispatching: {}", ex))

    @staticmethod
    def on_disconnect(client, userdata, rc):
        lg.info(string_write("MQ.Disconnection: client:{} userdata:[{}] rc:{}", client, userdata, rc))
        if 0 != rc:
            lg.info(string_write("MQ.Disconnection: disconnection error"))

    @staticmethod
    def on_log(client, userdata, level, buf):
        mqlog_map(lg, level, buf)

    @staticmethod
    def on_publish(client, userdata, mid):
        lg.info(string_write("MQ.Publish: client:{} userdata:[{}], mid:{}", client, userdata, mid))

    @staticmethod
    def on_subscribe(client, userdata, mid, granted_qos):
        lg.info(string_write("MQ.Subscribe: client:{} userdata:[{}], mid:{}, grated_qos:{}", client, userdata, mid, granted_qos))

    def teardown(self):
        try:
            if MonitorController.initialized:
                self.__subscriber.disconnect()
        except Exception as ex:
            lg.error(string_write("Exception on teardown: {}", ex))

    def __del__(self): pass

    def __str__(self): return string_write("clientid:[{}] host:[{}]", self.clientid, self.host)
    
    def create_mqtt_subscriber(self, host, port):
        self.__subscriber = mqtt.Client(self.clientid, True, self)
        self.__subscriber.on_connect    = MonitorController.on_connect
        self.__subscriber.on_message    = MonitorController.on_message
        self.__subscriber.on_disconnect = MonitorController.on_disconnect
        self.__subscriber.on_log        = MonitorController.on_log
        self.__subscriber.on_publish    = MonitorController.on_publish
        self.__subscriber.on_subscribe  = MonitorController.on_subscribe
        self.__subscriber.connect(host, port)
        self.__subscriber.subscribe([
            (INUITHY_TOPIC_HEARTBEAT,     self.tcfg.mqtt_qos),
            (INUITHY_TOPIC_UNREGISTER,    self.tcfg.mqtt_qos),
            (INUITHY_TOPIC_STATUS,        self.tcfg.mqtt_qos),
            (INUITHY_TOPIC_REPORTWRITE,   self.tcfg.mqtt_qos),
            (INUITHY_TOPIC_NOTIFICATION,  self.tcfg.mqtt_qos),
        ])

    def register_routes(self):
        self.topic_routes = {
            INUITHY_TOPIC_HEARTBEAT:      self.on_topic_heartbeat,
            INUITHY_TOPIC_UNREGISTER:     self.on_topic_unregister,
            INUITHY_TOPIC_STATUS:         self.on_topic_status,
            INUITHY_TOPIC_REPORTWRITE:    self.on_topic_reportwrite,
            INUITHY_TOPIC_NOTIFICATION:   self.on_topic_notification,
        }

    def __do_init(self):
        """
        __host: IP address of agent
        __clientid: identity in MQ network
        __expected_agents: list of agents
        __available_agents: agentid => AgentInfo
        """
        lg.info(string_write("Do initialization"))
        try:
            self.__expected_agents = self.trcfg.target_agents
            self.__host = socket.gethostname()
            self.__clientid = string_write(INUITHYCONTROLLER_CLIENT_ID, self.host)
            self.register_routes()
            self.create_mqtt_subscriber(*self.tcfg.mqtt)
            MonitorController.initialized = True
        except Exception as ex:
            lg.error(string_write("Failed to initialize: {}", ex))

    def load_configs(self, inuithy_cfgpath, traffic_cfgpath):
        is_configured = True
        try:
            self.__inuithy_cfg    = InuithyConfig(inuithy_cfgpath)
            if False == self.__inuithy_cfg.load():
                lg.error(string_write("Failed to load inuithy configure"))
                return False
            self.__traffic_cfg  = TrafficConfig(traffic_cfgpath) 
            if False == self.__traffic_cfg.load():
                lg.error(string_write("Failed to load traffics configure"))
                return False
            self.__network_cfg  = NetworkConfig(self.__traffic_cfg.nw_cfgpath) 
            if False == self.__network_cfg.load():
                lg.error(string_write("Failed to load network configure"))
                return False
            self.__current_nwlayout = ('', '')
            self.node_to_host()
            is_configured = True
        except Exception as ex:
            lg.error(string_write("Configure failed: {}", ex))
            is_configured = False
        return is_configured

    def load_storage(self):
        lg.error(string_write("Load DB plugin:{}", self.tcfg.storagetype))
        self.__storage = Storage(self.tcfg, lg)

    def __init__(self, inuithy_cfgpath='config/inuithy.conf', traffic_cfgpath='config/traffics.conf', lgr=None):
        global lg
        MonitorController.__initialized = False
        self.__node2host = {}
        self.__available_agents = {}
        self.__storage = None
        if lgr != None: lg = lgr
        #FIXME
        lg = logging
        if self.load_configs(inuithy_cfgpath, traffic_cfgpath):
            self.__do_init()

    def node_to_host(self):
        lg.info("Map node address to host")
        for agent in self.nwcfg.agents:
            [self.__node2host.__setitem__(node, agent[CFGKW_HOST]) for node in agent[CFGKW_NODES]]

    def is_network_layout_done(self):
        lg.info("Is network layout done")
        #TODO
        return False

    def is_traffic_all_set(self):
        lg.info("Is traffic all set")
        return True

    def start(self):
        if not MonitorController.initialized:
            lg.error(string_write("MonitorController not initialized"))
            return
        try:
            lg.info(string_write("Expected Agents({}): {}", len(self.__expected_agents), self.__expected_agents))
            self.__alive_notification()
            self.__subscriber.loop_forever()
        except KeyboardInterrupt:
            lg.info(string_write("MonitorController received keyboard interrupt"))
        except Exception as ex:
            lg.error(string_write("Exception on MonitorController: {}", ex))
        finally:
            self.teardown()
            lg.info(string_write("MonitorController terminated"))

    def add_agent(self, agentid, host, nodes):
        self.__available_agents[agentid] = AgentInfo(agentid, host, AgentStatus.ONLINE, nodes)
        lg.info(string_write("Agent {} added", agentid))

    def del_agent(self, agentid):
        if self.__available_agents.get(agentid):
            del self.__available_agents[agentid]
            lg.info(string_write("Agent {} removed", agentid))

    def is_agents_all_up(self):
        lg.info("Is agent all up")
        lg.debug(string_write("Expected Agents({}): {}", len(self.__expected_agents), self.__expected_agents))
        lg.debug(string_write("Available Agents({}): {}",
            len(self.__available_agents),
            [str(a) for a in self.__available_agents.values()]))

        if len(self.__expected_agents) != len(self.__available_agents):
            return False

        exps = []
        for aname in self.__expected_agents:
            agent = self.nwcfg.agent_by_name(aname)
            exps.append(agent[CFGKW_HOST])
        avails = []
        for ai in self.__available_agents.values():
            if ai.host not in exps: return False
        if self.tcfg.enable_localdebug:
            return True

        return True

    def on_topic_heartbeat(self, message):
        """Heartbeat message format:
        """
        lg.info(string_write("On topic heartbeat"))
        data = extract_payload(message.payload)
        agentid, host, nodes = data[CFGKW_CLIENTID], data[CFGKW_HOST], data[CFGKW_NODES]
        try:
            agentid = agentid.strip('\t\n ')
            self.add_agent(agentid, host, nodes)
        except Exception as ex:
            lg.error(string_write("Exception on registering agent {}: {}", agentid, ex))


    def on_topic_unregister(self, message):
        """Unregister message format:
        <agentid>
        """
        lg.info(string_write("On topic unregister"))
        data = extract_payload(message.payload)
        agentid, host, nodes = data[CFGKW_CLIENTID], data[CFGKW_HOST], data[CFGKW_NODES]
        try:
            self.del_agent(agentid)
            lg.info(string_write("Available Agents({}): {}", len(self.__available_agents), self.__available_agents))
        except Exception as ex:
            lg.error(string_write("Exception on unregistering agent {}: {}", agentid, ex))

    def on_topic_status(self, message):
        lg.info(string_write("On topic status"))
        lg.debug(message.payload)
        #TODO

    def on_topic_reportwrite(self, message):
        lg.info(string_write("On topic reportwrite"))
        data = extract_payload(message.payload)
        self.storage.insert_record(data)

    def on_topic_notification(self, message):
        lg.info(string_write("On topic notification"))
        data = extract_payload(message.payload)
        self.storage.insert_record(data)

    def __alive_notification(self):
        """Broadcast on new controller startup
        """
        lg.info(string_write("New controller notification {}", self.clientid))
        data = {
            CFGKW_CTRLCMD:  CtrlCmds.NEW_CONTROLLER.name,
            CFGKW_CLIENTID: self.clientid,
        }
        pub_ctrlcmd(self.__subscriber, self.tcfg.mqtt_qos, data)

def start_controller(tcfg, trcfg):
    controller = MonitorController(tcfg, trcfg)
    controller.start()

if __name__ == '__main__':
    lg.info(string_write(INUITHY_TITLE, INUITHY_VERSION, "MonitorController"))
    start_controller(INUITHY_CONFIG_PATH, TRAFFIC_CONFIG_PATH)

