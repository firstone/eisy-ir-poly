from enum import Enum
from threading import Thread
import udi_interface
from udi_interface import LOGGER
import usb.core
import usb.util
import yaml


class Controller(udi_interface.Node):

    VENDOR_ID = 0x20a0
    PRODUCTS = [
        {
            'ID': 0x0001,
            'interface': 0,
            'desc': 'Flirc V1'
        },
        {
            'ID': 0x0006,
            'interface': 1,
            'desc': 'Flirc V2'
        },
    ]
    DEFAULT_TIMEOUT = 5000

    def __init__(self, polyglot, primary, address, name):
        super(Controller, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.buttons = {}
        self.active_button = None
        self.dev_endpoint = None
        self.timeout = Controller.DEFAULT_TIMEOUT
        self.key_codes = {}

        with open('scancodes.yaml', 'r') as f:
            self.key_codes = yaml.safe_load(f)

        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        polyglot.subscribe(polyglot.CUSTOMTYPEDDATA, self.parameter_handler)
        polyglot.subscribe(polyglot.POLL, self.poll)

        udi_interface.Custom(polyglot, "customtypedparams").load([
            {
                'name': 'idleThreshold',
                'title': 'Idle Threshold',
                'desc':
                'Threshold (in ms) before pressed or released key state becomes idle',
                'isRequired': True,
                'defaultValue': Controller.DEFAULT_TIMEOUT
            },
        ], True)

        polyglot.ready()
        polyglot.addNode(self, conn_status="ST")

    def discover(self, *args, **kwargs):
        pass

    def query(self):
        super(Controller, self).query()
        for key in self.buttons.values():
            key.query()

    def start(self):
        self.is_running = True

        self.poly.updateProfile()
        self.poly.Notices.clear()
        self.poly.setCustomParamsDoc()

        self.setDriver('ST', 0)
        LOGGER.info('Started eISY IR Server')

        self.connect()

    def stop(self):
        self.is_running = False

    def connect(self):
        for product in Controller.PRODUCTS:
            if self.connect_dev(product):
                LOGGER.info(f'{product["desc"]} connected')
                self.poly.Notices.clear()
                self.setDriver('ST', 1)
                Thread(target=self.poll_flirc).start()
                return

        self.poly.Notices[
            'device'] = 'Could not connect Flirc device. Make sure device is plugged in and permissioans are set'

    def connect_dev(self, product) -> bool:
        self.dev = usb.core.find(idVendor=Controller.VENDOR_ID,
                                 idProduct=product['ID'])
        if self.dev is None:
            return False

        self.dev_endpoint = self.dev[0][(product['interface'], 0)][0]
        return True

    def poll(self, pollflag):
        if self.dev_endpoint is None:
            self.connect()

    def parameter_handler(self, params):
        if params is not None:
            self.timeout = params.get('idleThreshold')

        if self.timeout is None:
            self.timeout = Controller.DEFAULT_TIMEOUT

    def poll_flirc(self):
        while self.is_running:
            try:
                buffer = self.dev.read(self.dev_endpoint.bEndpointAddress, 8,
                                       self.timeout).tobytes()
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
                    button = IRButton(self.poly, self.address, button_code,
                                      desc)
                    self.buttons[button_code] = button
                    self.poly.addNode(button)

                self.active_button = button
                button.press()
            except usb.core.USBTimeoutError:
                for button in self.buttons.values():
                    button.idle()

    id = 'controller'
    commands = {'QUERY': query}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


class KeyState(Enum):
    IDLE = 0
    PRESSED = 1
    HELD = 2
    RELEASED = 3


class IRButton(udi_interface.Node):

    def __init__(self, primary, controller_address, code, desc):
        super(IRButton,
              self).__init__(primary, controller_address,
                             f'irbutton_{hex(code)[2:]}', f'IR Button {desc}')
        self.code = code
        self.desc = desc
        self.state = KeyState.IDLE
        self.press_count = 0

    def set_state(self):
        LOGGER.debug(f'{self.desc} {self.state}')
        self.setDriver('ST', self.state.value)

    def query(self):
        self.reportDrivers()

    def press(self):
        if self.press_count > 3:
            if self.state != KeyState.HELD:
                self.state = KeyState.HELD
                self.set_state()
        else:
            self.press_count += 1

    def release(self):
        self.press_count = 0
        if self.state == KeyState.HELD:
            self.state = KeyState.RELEASED
        else:
            self.state = KeyState.PRESSED

        self.set_state()

    def idle(self):
        if self.state != KeyState.IDLE:
            self.state = KeyState.IDLE
            self.set_state()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 25}]

    id = 'irbutton'


def eisy_ir_server():
    polyglot = udi_interface.Interface([])
    polyglot.start("0.1.2")
    Controller(polyglot, "controller", "controller", "eISY IR Controller")
    polyglot.runForever()


if __name__ == '__main__':
    eisy_ir_server()
