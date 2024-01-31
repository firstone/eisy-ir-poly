from threading import Thread
import time
import udi_interface
from udi_interface import LOGGER
import usb.core
import usb.util
import yaml

from ir_button import IRButton, KeyState


class Controller(udi_interface.Node):

    VENDOR_ID = 0x20a0
    HELD_THRESHOLD = 500
    IDLE_THRESHOLD = 500
    RELEASE_THRESHOLD = 300

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        self.buttons = {}
        self.active_buttons = {}
        self.active_button = None
        self.dev_endpoint = None
        self.idle_threshold = Controller.IDLE_THRESHOLD
        self.held_threshold = Controller.HELD_THRESHOLD
        self.release_threshold = Controller.RELEASE_THRESHOLD
        self.key_codes = {}
        self.is_running = False
        self.dev = None

        with open('scancodes.yaml', 'r', encoding='utf-8') as f:
            self.key_codes = yaml.safe_load(f)

        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        polyglot.subscribe(polyglot.CONFIG, self.config_handler)
        polyglot.subscribe(polyglot.CUSTOMTYPEDDATA, self.parameter_handler)
        polyglot.subscribe(polyglot.POLL, self.poll)

        udi_interface.Custom(polyglot, "customtypedparams").load([
            {
                'name': 'idleThreshold',
                'title': 'Idle Threshold',
                'desc':
                'Threshold (in ms) before pressed or released key state becomes idle',
                'isRequired': True,
                'defaultValue': Controller.IDLE_THRESHOLD
            },
            {
                'name': 'pressThreshold',
                'title': 'Press Threshold',
                'desc': 'Threshold (in ms) before pressed button becomes held',
                'isRequired': True,
                'defaultValue': Controller.HELD_THRESHOLD
            },
            {
                'name': 'releaseThreshold',
                'title': 'Release Threshold',
                'desc': 'Threshold (in ms) before button release registers',
                'isRequired': True,
                'defaultValue': Controller.RELEASE_THRESHOLD
            },
        ], True)

        polyglot.ready()
        polyglot.addNode(self, conn_status="ST")

    def discover(self, *args, **kwargs):
        pass

    def query(self):
        super().query()
        for key in self.buttons.values():
            key.query()

    def start(self):
        self.poly.updateProfile()
        self.poly.Notices.clear()
        self.poly.setCustomParamsDoc()

        self.setDriver('ST', 0)
        LOGGER.info('Started eISY IR Server')

        self.connect()

    def config_handler(self, config):
        for node in config.get('nodes', {}):
            if not node['isPrimary']:
                button_code = int(node['address'][9:], 16)
                desc = node['name'][10:]
                button = IRButtonNode(self, button_code, desc)
                self.buttons[button_code] = button
                self.poly.addNode(button)
                button.idle()

    def stop(self):
        self.is_running = False
        try:
            if self.dev is not None:
                self.dev.reset()
        except Exception:
            pass
        for button in self.buttons.values():
            button.offline()

    def connect(self):
        try:
            self.is_running = False
            self.dev = usb.core.find(idVendor=Controller.VENDOR_ID)
            if self.dev is None:
                raise RuntimeError('Device not found')

            interface_num = None
            self.dev_endpoint = None

            for interface in self.dev[0].interfaces():
                if interface.bInterfaceClass == 3:
                    if interface[0].wMaxPacketSize == 8:
                        interface_num = interface.bInterfaceNumber
                        self.dev_endpoint = interface[0]
                        break

            if self.dev_endpoint is None:
                raise RuntimeError('Cannot find interface')

            LOGGER.info('Connected device version %s interface# %d',
                        self.dev.idProduct, interface_num)
            self.poly.Notices.clear()
            self.is_running = True
            Thread(target=self.poll_flirc).start()
            Thread(target=self.tick).start()
            self.setDriver('ST', 1)
        except Exception as e:
            LOGGER.error(e)
            self.poly.Notices[
                'device'] = 'Could not connect Flirc device. Make sure device is plugged \
                             in and permissioans are set'

    def disconnect(self):
        self.setDriver('ST', 0)
        self.is_running = False
        self.dev = None
        self.dev_endpoint = None

    #pylint: disable=unused-argument
    def poll(self, pollflag):
        if self.dev_endpoint is None:
            self.connect()

    def set_param(self, params, name, default):
        try:
            val = int(params.get(name))
        except Exception:
            val = default

        LOGGER.debug('%s set to %s', name, val)

        return val

    def parameter_handler(self, params):
        self.idle_threshold = self.set_param(params, 'idleThreshold',
                                             Controller.IDLE_THRESHOLD)
        self.held_threshold = self.set_param(params, 'pressThreshold',
                                             Controller.HELD_THRESHOLD)
        self.release_threshold = self.set_param(params, 'releaseThreshold',
                                                Controller.RELEASE_THRESHOLD)

    def tick(self):
        while self.is_running:
            for button in list(self.active_buttons.values()):
                button.tick()
                if button.is_idle():
                    del self.active_buttons[button.code]
            time.sleep(0.001)

    def poll_flirc(self):
        while self.is_running:
            try:
                buffer = self.dev.read(self.dev_endpoint.bEndpointAddress, 8,
                                       0).tobytes()
                LOGGER.debug(buffer.hex())
                if buffer[0] == 2:
                    code = buffer[1]
                    code_dict = self.key_codes['Special Keys']
                else:
                    code = buffer[2]
                    code_dict = self.key_codes

                if code == 0:
                    if self.active_button is not None:
                        self.active_button.release()
                        self.active_button = None
                    continue

                button_code = buffer[0] << 8 | code
                button = self.buttons.get(button_code)
                if button is None:
                    desc = code_dict.get(code)
                    if desc is None:
                        desc = f'code {code}'
                    elif not isinstance(desc, str):
                        desc = desc[0]
                    button = IRButtonNode(self, button_code, desc)
                    self.buttons[button_code] = button
                    self.poly.addNode(button)

                button.press()
                self.active_button = button
                self.active_buttons[button_code] = button
            except Exception as e:
                if self.is_running:
                    LOGGER.exception(e)
                self.disconnect()

    id = 'controller'
    commands = {'QUERY': query}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25}]


class IRButtonNode(udi_interface.Node):

    def __init__(self, controller, code, desc):
        super().__init__(controller.poly, controller.address,
                         f'irbutton_{hex(code)[2:]}', f'IR Button {desc}')
        self.button = IRButton(controller, IRButtonNode.timer)
        self.controller = controller
        self.code = code
        self.desc = desc

    def set_state(self):
        LOGGER.debug('setting %s to state %s', self.desc, self.button.state)
        self.setDriver('ST', self.button.state.value)
        if self.button.state not in (KeyState.IDLE, KeyState.OFFLINE):
            self.reportCmd(f'GV{self.button.state.value}')

    def query(self):
        self.reportDrivers()

    @staticmethod
    def timer():
        return int(time.time_ns() / 1000000)

    def idle(self):
        self.button.idle()
        self.set_state()

    def offline(self):
        self.button.offline()
        self.set_state()

    def is_idle(self):
        return self.button.is_idle()

    def tick(self):
        if self.button.tick():
            LOGGER.debug('change detected %s %s', self.desc, self.button.state)
            self.set_state()

    def press(self):
        self.button.press()

    def release(self):
        self.button.release()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25}]

    id = 'irbutton'


def eisy_ir_server():
    polyglot = udi_interface.Interface([])
    polyglot.start("1.2.0")
    Controller(polyglot, "controller", "controller", "eISY IR Controller")
    polyglot.runForever()


if __name__ == '__main__':
    eisy_ir_server()
