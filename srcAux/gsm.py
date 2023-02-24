# Imports
import time
import json

class GenericATError(Exception):
    pass


class Response(object):

    def __init__(self, status_code, content):
        self.status_code = int(status_code)
        self.content     = content
        
class Modem(object):

    def __init__(self, uart=None, MODEM_PWKEY_PIN=None, MODEM_RST_PIN=None, MODEM_POWER_ON_PIN=None, MODEM_TX_PIN=None, MODEM_RX_PIN=None):

        # Pins
        self.MODEM_PWKEY_PIN    = MODEM_PWKEY_PIN
        self.MODEM_RST_PIN      = MODEM_RST_PIN
        self.MODEM_POWER_ON_PIN = MODEM_POWER_ON_PIN
        self.MODEM_TX_PIN       = MODEM_TX_PIN
        self.MODEM_RX_PIN       = MODEM_RX_PIN

        # Uart
        self.uart = uart

        self.initialized = False
        self.modem_info = None
        self.udp_ip = ""
        self.values = {"GSMSignal":"", "latitude":"", "longitude":"",
                    "altitude":"", "speed":"", "course":"", "GPSFix":""}


    #----------------------
    #  Modem initializer
    #----------------------

    def updateUdpIp(self, new_ip):
        self.uart.write("AT+CIPSHUT\n")
        self.udp_ip = new_ip

    def initialize(self):
        print("DEBUG: Initializing modem...")    

        if not self.uart:
            from machine import UART, Pin

            # Pin initialization
            MODEM_PWKEY_PIN_OBJ = Pin(self.MODEM_PWKEY_PIN, Pin.OUT) if self.MODEM_PWKEY_PIN else None
            MODEM_RST_PIN_OBJ = Pin(self.MODEM_RST_PIN, Pin.OUT) if self.MODEM_RST_PIN else None
            MODEM_POWER_ON_PIN_OBJ = Pin(self.MODEM_POWER_ON_PIN, Pin.OUT) if self.MODEM_POWER_ON_PIN else None
            #MODEM_TX_PIN_OBJ = Pin(self.MODEM_TX_PIN, Pin.OUT) # Not needed as we use MODEM_TX_PIN
            #MODEM_RX_PIN_OBJ = Pin(self.MODEM_RX_PIN, Pin.IN)  # Not needed as we use MODEM_RX_PIN

            # Status setup
            if MODEM_PWKEY_PIN_OBJ:
                MODEM_PWKEY_PIN_OBJ.value(0)
            if MODEM_RST_PIN_OBJ:
                MODEM_RST_PIN_OBJ.value(1)
            if MODEM_POWER_ON_PIN_OBJ:
                MODEM_POWER_ON_PIN_OBJ.value(1)

            # Setup UART
            print("SETUP UART")
            self.uart = UART(1, 115200, timeout=1000, rx=self.MODEM_TX_PIN, tx=self.MODEM_RX_PIN, timeout_char = 5)

        # Test AT commands
        time.sleep_ms(500)
        retries = 0
        while True:
            try:
                self.modem_info = self.execute_at_command('modeminfo')
            except:
                retries+=1
                if retries < 3:
                    print('DEBUG: Error in getting modem info, retrying.. (#{})'.format(retries))
                    time.sleep(1)
                else:
                    raise
            else:
                break

        print("DEBUG: Modem is ready")
        # Set initialized flag and support vars
        self.initialized = True
        time.sleep(2)
        self.uart.read()
        #Makes the gsm reject everycall so it doesn't interfere with the message response
        # # Check if SSL is supported
        self.ssl_available = self.execute_at_command('checkssl') == '+CIPSSL: (0-1)'
        self.uart.read()

    def setupGSM(self):
        time.sleep_ms(500)
        self.execute_at_command('pin')
        time.sleep_ms(500)
        self.uart.read()
        self.connect('net2.vodafone.pt', user='vodafone',pwd='vodafone')
        time.sleep_ms(500)
        self.uart.read()
        self.execute_at_command('setbusy')
        time.sleep_ms(500)
        self.uart.read()
        # self.values["PhoneNumber"]=self.execute_at_command('phonenumber').split(',')[1].replace('\"', '')
        time.sleep_ms(500)
        self.uart.read()
        # self.values['IPExtern']=self.get_ip_addr()
        time.sleep_ms(500)
        self.uart.read()
        # self.values['IMEI'] = self.execute_at_command('imei')
        time.sleep_ms(500)
        self.uart.read()
        self.execute_at_command('turngpson')
        time.sleep_ms(500)
        self.uart.read()
        self.execute_at_command('inithttp')
        time.sleep_ms(500)
        self.uart.read()
        self.execute_at_command('sethttp')
        time.sleep_ms(500)
        self.execute_at_command('enablessl')
        
    #----------------------
    # Execute AT commands
    #----------------------
    def execute_at_command(self, command, data=None, clean_output=True):
        # Commands dictionary. Not the best approach ever, but works nicely.
        commands = {
                    'modeminfo':  {'string':'AT', 'timeout':3, 'end': 'OK'},
                    'fwrevision': {'string':'AT+CGMR', 'timeout':3, 'end': 'OK'},
                    'battery':    {'string':'AT+CBC', 'timeout':3, 'end': 'OK'},
                    'scan':       {'string':'AT+COPS=?', 'timeout':60, 'end': 'OK'},
                    'network':    {'string':'AT+COPS?', 'timeout':3, 'end': 'OK'},
                    'signal':     {'string':'AT+CSQ', 'timeout':3, 'end': 'OK'},
                    'setbusy':    {'string':'AT+GSMBUSY = 1', 'timeout':3, 'end':'OK'},
                    'checkreg':   {'string':'AT+CREG?', 'timeout':3, 'end': None},
                    'setapn':     {'string':'AT+SAPBR=3,1,"APN","{}"'.format(data), 'timeout':3, 'end': 'OK'},
                    'setuser':    {'string':'AT+SAPBR=3,1,"USER","{}"'.format(data), 'timeout':3, 'end': 'OK'},
                    'setpwd':     {'string':'AT+SAPBR=3,1,"PWD","{}"'.format(data), 'timeout':3, 'end': 'OK'},
                    'initgprs':   {'string':'AT+SAPBR=3,1,"Contype","GPRS"', 'timeout':3, 'end': 'OK'}, # Appeared on hologram net here or below
                    'opengprs':   {'string':'AT+SAPBR=1,1', 'timeout':3, 'end': 'OK'},
                    'getbear':    {'string':'AT+SAPBR=2,1', 'timeout':3, 'end': 'OK'},
                    'inithttp':   {'string':'AT+HTTPINIT', 'timeout':3, 'end': 'OK'},
                    'sethttp':    {'string':'AT+HTTPPARA="CID",1', 'timeout':3, 'end': 'OK'},
                    'checkssl':   {'string':'AT+CIPSSL=?', 'timeout': 3, 'end': 'OK'},
                    'enablessl':  {'string':'AT+HTTPSSL=1', 'timeout':3, 'end': 'OK'},
                    'disablessl': {'string':'AT+HTTPSSL=0', 'timeout':3, 'end': 'OK'},
                    'initurl':    {'string':'AT+HTTPPARA="URL","{}"'.format(data), 'timeout':3, 'end': 'OK'},
                    'doget':      {'string':'AT+HTTPACTION=0', 'timeout':3, 'end': '+HTTPACTION'},
                    'setcontent': {'string':'AT+HTTPPARA="CONTENT","{}"'.format(data), 'timeout':3, 'end': 'OK'},
                    'postlen':    {'string':'AT+HTTPDATA={},5000'.format(data), 'timeout':3, 'end': 'DOWNLOAD'},  # "data" is data_lenght in this context, while 5000 is the timeout
                    'dumpdata':   {'string':data, 'timeout':1, 'end': 'OK'},
                    'dopost':     {'string':'AT+HTTPACTION=1', 'timeout':3, 'end': '+HTTPACTION'},
                    'getdata':    {'string':'AT+HTTPREAD', 'timeout':3, 'end': 'OK'},
                    'closehttp':  {'string':'AT+HTTPTERM', 'timeout':3, 'end': 'OK'},
                    'closebear':  {'string':'AT+SAPBR=0,1', 'timeout':3, 'end': 'OK'},
                    'phonenumber':{'string':'AT+CNUM', 'timeout':3, 'end': 'OK'},
                    'imei':       {'string':'AT+GSN', 'timeout':3, 'end': 'OK'}, 
                    'pin':        {'string':'AT+CPIN=1379', 'timeout':3, 'end': 'OK'},
                    'turngpson':  {'string':'AT+CGPSPWR=1', 'timeout':3, 'end': 'OK'},
                    'gpsstatus':  {'string':'AT+CGPSSTATUS?', 'timeout':0.5, 'end': 'OK'},
                    'gpscoord':   {'string':'AT+CGNSINF', 'timeout':0.5, 'end': 'OK'},
                    'gpstime':    {'string':'AT+CGPSINF=0', 'timeout':3, 'end': 'OK'},
                    'keepalive':  {'string':'AT+SHAHEAD="Connection keep-alive"','timeout':3, 'end': 'OK'}
        }

        # References:
        # https://github.com/olablt/micropython-sim800/blob/4d181f0c5d678143801d191fdd8a60996211ef03/app_sim.py
        # https://arduino.stackexchange.com/questions/23878/what-is-the-proper-way-to-send-data-through-http-using-sim908
        # https://stackoverflow.com/questions/35781962/post-api-rest-with-at-commands-sim800
        # https://arduino.stackexchange.com/questions/34901/http-post-request-in-json-format-using-sim900-module (full post example)

        # Sanity checks
        if command not in commands:
            raise Exception('Unknown command "{}"'.format(command))

        # Support vars
        command_string  = commands[command]['string']
        excpected_end   = commands[command]['end']
        timeout         = commands[command]['timeout']
        processed_lines = 0

        # Execute the AT command
        if command != 'dumpdata':
            command_string_for_at = "{}\r\n".format(command_string)
        else:
            command_string_for_at = "{}".format(command_string)

        # print('Writing AT command "{}"'.format(command_string_for_at.encode('utf-8')))
        self.uart.write(command_string_for_at)

        # Support vars
        pre_end = True
        output  = ''
        empty_reads = 0

        while True:
            line = self.uart.readline()
            if not line:
                time.sleep(0.1)
                empty_reads += 1
                if empty_reads > timeout:
                    raise Exception('Timeout for command "{}" (timeout={})'.format(command, timeout))
                    #logger.warning('Timeout for command "{}" (timeout={})'.format(command, timeout))
                    #break
            else:
                # Convert line to string
                try:
                    line_str = line.decode('utf-8')
                    # print('line_str "{}"'.format(line_str))
                except:
                    line_str = ""
                    # print("An exception occurred")
                    pass
                # Do we have an error?
                if line_str == 'ERROR\r\n':
                    # print('Got generic AT error')
                    break
                    # raise GenericATError('Got generic AT error')

                # If we had a pre-end, do we have the expected end?
                if line_str == '{}\r\n'.format(excpected_end):
                    # print('Detected exact end')
                    break
                if pre_end and line_str.startswith('{}'.format(excpected_end)):
                    # print('Detected startwith end (and adding this line to the output too)')
                    output += line_str
                    break

                # Do we have a pre-end?
                if line_str == '\r\n':
                    pre_end = True
                    # print('Detected pre-end')
                else:
                    pre_end = False

                # Keep track of processed lines and stop if exceeded
                processed_lines+=1

                # Save this line unless in particular conditions
                if command == 'getdata' and line_str.startswith('+HTTPREAD:'):
                    pass
                else:
                    output += line_str

        # Remove the command string from the output
        output = output.replace(command_string+'\r\r\n', '')
        # ..and remove the last \r\n added by the AT protocol
        if output.endswith('\r\n'):
            output = output[:-2]

        # Also, clean output if needed
        if clean_output:
            output = output.replace('\r', '')
            output = output.replace('\n\n', '')
            if output.startswith('\n'):
                output = output[1:]
            if output.endswith('\n'):
                output = output[:-1]

        # print('Returning "{}"'.format(output.encode('utf8')))

        # Retur
        return output

    #----------------------
    #  Function commands
    #----------------------

    def get_info(self):
        output = self.execute_at_command('modeminfo')
        return output

    def battery_status(self):
        output = self.execute_at_command('battery')
        return output

    def scan_networks(self):
        networks = []
        output = self.execute_at_command('scan')
        pieces = output.split('(', 1)[1].split(')')
        for piece in pieces:
            piece = piece.replace(',(','')
            subpieces = piece.split(',')
            if len(subpieces) != 4:
                continue
            networks.append({'name': json.loads(subpieces[1]), 'shortname': json.loads(subpieces[2]), 'id': json.loads(subpieces[3])})
        return networks

    def get_current_network(self):
        output = self.execute_at_command('network')
        network = output.split(',')[-1]
        if network.startswith('"'):
            network = network[1:]
        if network.endswith('"'):
            network = network[:-1]
        # If after filtering we did not filter anything: there was no network
        if network.startswith('+COPS'):
            return None
        return network

    def get_signal_strength(self):
        # See more at https://m2msupport.net/m2msupport/atcsq-signal-quality/
        output = self.execute_at_command('signal')
        signal = int(output.split(':')[1].split(',')[0])
        signal_ratio = float(signal)/float(30) # 30 is the maximum value (2 is the minimum)
        return signal_ratio

    def get_ip_addr(self):
        output = self.execute_at_command('getbear')
        output = output.split('+')[-1] # Remove potential leftovers in the buffer before the "+SAPBR:" response
        pieces = output.split(',')
        if len(pieces) != 3:
            raise Exception('Cannot parse "{}" to get an IP address'.format(output))
        ip_addr = pieces[2].replace('"','')
        if len(ip_addr.split('.')) != 4:
            raise Exception('Cannot parse "{}" to get an IP address'.format(output))
        if ip_addr == '0.0.0.0':
            return None
        return ip_addr

    def connect(self, apn, user='', pwd=''):
        if not self.initialized:
            raise Exception('Modem is not initialized, cannot connect')

        # Are we already connected?
        if self.get_ip_addr():
            print('Modem is already connected, not reconnecting.')
            return

        # Closing bearer if left opened from a previous connect gone wrong:
        # print('Trying to close the bearer in case it was left open somehow..')
        try:
            self.execute_at_command('closebear')
        except GenericATError:
            pass

        # First, init gprs
        # print('Connect step #1 (initgprs)')
        self.execute_at_command('initgprs')

        # Second, set the APN
        # print('Connect step #2 (setapn)')
        self.execute_at_command('setapn', apn)
        self.execute_at_command('setuser', user)
        self.execute_at_command('setpwd', pwd)

        # Then, open the GPRS connection.
        # print('Connect step #3 (opengprs)')
        self.execute_at_command('opengprs')

        # Ok, now wait until we get a valid IP address
        retries = 0
        max_retries = 5
        while True:
            ip_addr = self.get_ip_addr()
            if not ip_addr:
                retries += 1
                if retries > max_retries:
                    raise Exception('Cannot connect modem as could not get a valid IP address')
                print('DEBUG: No valid IP address yet, retrying... (#')
                time.sleep(1)
            else:
                break

    def disconnect(self):

        # Close bearer
        try:
            self.execute_at_command('closebear')
        except GenericATError:
            pass

        # Check that we are actually disconnected
        ip_addr = self.get_ip_addr()
        if ip_addr:
            raise Exception('Error, we should be disconnected but we still have an IP address ({})'.format(ip_addr))

    def http_request(self, url, mode='GET', data=None, content_type='application/json'):

        # Protocol check.
        assert url.startswith('http'), 'Unable to handle communication protocol for URL "{}"'.format(url)

        # Are we  connected?
        # if not self.get_ip_addr():
            # raise Exception('Error, modem is not connected')

        # Close the http context if left open somehow
        # print('Close the http context if left open somehow...')
        # try:
        #     start = time.ticks_ms()
        #     self.execute_at_command('closehttp')
        #     self.printTime(start)
        # except GenericATError:
        #     pass

        # First, init and set http
        # print('Http request step #1.1 (inithttp)')
        # start = time.ticks_ms()
        # self.execute_at_command('inithttp')
        # self.printTime(start)
        print('Http request step #1.2 (sethttp)')
        # start = time.ticks_ms()
        # self.execute_at_command('sethttp')
        # self.printTime(start)
        start = time.ticks_ms()
        # Do we have to enable ssl as well?
        if self.ssl_available:
            if url.startswith('https://'):
                # print('Http request step #1.3 (enablessl)')
                self.execute_at_command('enablessl')
            elif url.startswith('http://'):
                # print('Http request step #1.3 (disablessl)')
                self.execute_at_command('disablessl')
        else:
            if url.startswith('https://'):
                raise NotImplementedError("SSL is only supported by firmware revisions >= R14.00")
        print(time.ticks_ms() - start)
        # Second, init and execute the request
        print('Http request step #2.1 (initurl)')
        start = time.ticks_ms()
        self.execute_at_command('initurl', data=url)
        print(time.ticks_ms()-start)

        if mode == 'GET':

            # print('Http request step #2.2 (doget)')
            output = self.execute_at_command('doget')
            response_status_code = output.split(',')[1]
            # print('Response status code: "{}"'.format(response_status_code))

        elif mode == 'POST':

            print('Http request step #2.2 (setcontent)')
            start = time.ticks_ms()
            self.execute_at_command('setcontent', content_type)
            print(time.ticks_ms()-start) 
            print('Http request step #2.3 (postlen)')
            start = time.ticks_ms()
            self.execute_at_command('postlen', len(data))
            print(time.ticks_ms()-start)
            print('Http request step #2.4 (dumpdata)')
            start = time.ticks_ms()
            self.execute_at_command('dumpdata', data)
            print(time.ticks_ms()-start)
            print('Http request step #2.5 (dopost)')
            start = time.ticks_ms()
            output = self.execute_at_command('dopost')
            print(time.ticks_ms()-start)
            response_status_code = output.split(',')[1]
            print(time.ticks_ms()-start)  
            # print('Response status code: "{}"'.format(response_status_code))

        elif mode == 'UPD':
            self.execute_at_command('')
        else:
            raise Exception('Unknown mode "{}'.format(mode))

        # Third, get data
        print('Http request step #4 (getdata)')
        start = time.ticks_ms()
        # self.uart.read()
        response_content = {}
        response_content = self.execute_at_command('getdata', clean_output=False)
        print(time.ticks_ms()-start)
        print(response_content)

        # Then, close the http context
        # print('Http request step #4 (closehttp)')
        # start = time.ticks_ms()
        # self.execute_at_command('closehttp')
        # self.printTime(start)

        return Response(status_code=response_status_code, content = response_content)

    def getGpsStatus(self):
        response = self.execute_at_command('gpsstatus')
        # print("DEBUG->getGpsStatus : ({}".format(response))
        rsp = response.split(': ')
        if(len(rsp) > 0):
            self.values["GPSFix"] = rsp[1]

    def getGpsData(self):
        response = self.execute_at_command('gpscoord')
        print("DEBUG->getGpsData : ({}".format(response))
        fields = response.split(': ')
        gps_fields = fields[1].split(',')
        if len(gps_fields) > 8:
            # self.values["DateandTime"] = gps_fields[2]
            self.values["latitude"] = gps_fields[3]
            self.values["longitude"] = gps_fields[4]
            self.values["altitude"] = gps_fields[5]
            self.values["speed"] = gps_fields[6]
            self.values["course"] = gps_fields[7]

    def setupUDP(self):
        self.uart.write('AT+CSTT="net2.vodafone.pt"\n')
        time.sleep(0.01)
        self.uart.write('AT+CIICR\n')
        time.sleep(0.01)
        self.uart.write('AT+CIFSR\n')
        time.sleep(0.01)
        # 94.62.143.3
        self.uart.write('AT+CIPSTART="UDP",{},"5001"\n'.format(self.udp_ip))
        self.readAll()

    def sendToUDP(self, data):
        self.uart.write('AT+CIPSEND={}\n'.format(len(data)))
        time.sleep(0.01)
        self.uart.write('{}\n'.format(data))
        time.sleep(0.01)

    def readAll(self):
        line = self.uart.read()
        print(line)
        # try:
        #     line_str = line.decode('utf-8')
        #     print('line_str "{}"'.format(line_str))
        # except:
        #     line_str = ""
        #     break