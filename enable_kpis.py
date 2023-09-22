import requests
import yaml
import logging
import json
import configparser
import ast

# Create a logger
logger = logging.getLogger(__name__)

# Set the logging level
logger.setLevel(logging.INFO)

# Create a file handler
file_handler = logging.FileHandler('enable_kpis.log')

# Set the file handler's format
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))

# Add the file handler to the logger
logger.addHandler(file_handler)


# dcloud setup
CONFIG_FILE_PATH = "/Users/mfarook2/Desktop/CROSSWORK/CNC5.0/Enable_kpi_profiles/AUTO_ENABLE_NETWORK_PROFILES/config.yaml"

Ticket_Token_Header = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': "text/plain",
    'Cache-Control': "no-cache",
}

Ticket_Token_Header_JSON = {
    'Content-Type': 'application/json',
    'Accept': "text/plain",
    'Cache-Control': "no-cache",
}

def formatPayload(keylist):
    logger.info('formatpayload() : formatpayload')
    logger.info('TYPE keyList :: %s', type(keylist))
    value_list = ""
    for value in keylist:
        value_list += "\"" + value + "\"" + ","
    value_list = value_list.rstrip(",")
    return value_list

def build_kpi_list():
    with open(CONFIG_FILE_PATH) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        logger.info("YAML data Type: %s'", data)
        xr_object_names = []
        for key, value in (data['KPI']['XR']).items():
            xr_object_names.append(key)
        logger.info('XR KEYS  %s', xr_object_names)
        xe_object_names = []
        for key, value in (data['KPI']['IOS_XE']).items():
            xe_object_names.append(key)
        logger.info('XE KEYS  %s ', xe_object_names)
        return (data, xr_object_names, xe_object_names)

class Crosswork:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.crosswork_ip_address = config['crosswork']['ip_address']
        self.crosswork_port = config['crosswork']['port']
        self.crosswork_userid = config['crosswork']['userid']
        self.crosswork_password = config['crosswork']['password']
        self.crosswork_kpis = config['kpiprofile']['kpis']
        print('IP address ', self.crosswork_ip_address)
        print(' Port', self.crosswork_port)
        print('Userid ', self.crosswork_userid)
        print(' Password', self.crosswork_password)
        print(' KPIS', self.crosswork_kpis)
    

    def get_ticket(self):
        logger.info('getTicket() : Getting Ticket')
        url = "https://" \
              + self.crosswork_ip_address \
              + ":" \
              + str(self.crosswork_port) \
              + "/crosswork/sso/v1/tickets/"
        querystring = {"username": self.crosswork_userid,
                       "password": self.crosswork_password}
        payload = ""
        response = requests.request("POST", url,
                                    data=payload,
                                    headers=Ticket_Token_Header,
                                    params=querystring,
                                    verify=False)
        logger.info('getTicket() : return code  :: %s', response.text)
        return response.text

    def get_token(self):
        logger.info('getToken() : Getting Token')
        url = "https://" \
              + self.crosswork_ip_address \
              + ":" + str(self.crosswork_port) \
              + "/crosswork/sso/v1/tickets/" \
              + self.get_ticket()
        payload = "service=https%3A%2F%2F" \
                  + self.crosswork_ip_address \
                  + "%3A30603%2Fapp-dashboard&undefined="
        response = requests.request("POST",
                                    url,
                                    data=payload,
                                    headers=Ticket_Token_Header,
                                    verify=False)
        logger.info('getToken() : return code  :: %s', response.text)
        return response.text

    def get_devices_list(self):
        logger.info('get_devices_list() : Get the  list of all devices in CNC')
        url = "https://" \
                + self.crosswork_ip_address \
                + ":" + str(self.crosswork_port) \
                + "/crosswork/inventory/v1/nodes/query" \

        #payload = "service=https%3A%2F%2F" \
        #            + self.crosswork_ip_address \
        #            + "%3A30603%2Fapp-dashboard&undefined="
        payload = json.dumps({
            "filterData": {
                "inet_addr": self.crosswork_ip_address,
                "PageSize": 30,
                "PageNum": 0,
                "Criteria": ""
                }
                })
        headers = {'Content-Type': "application/json",
            'Authorization': "Bearer " + self.get_token(),
            'Cache-control': "no-cache",
            }
        response = requests.request("POST",
                                    url,
                                    data=payload,
                                    headers=headers,
                                    verify=False)
        data = response.json()
        device_list = []
        for device in data['data']:
            device_list.append(device['host_name'])
        logger.info('Device List Farook ::  %s', device_list)

        return device_list

    def create_kpi_profile(self):
        logger.info('create_kpi_profiles')

        KPI_PROFILE_STRUCTURE = '{\"id\": \"\",' \
                                ' \"name\": \"KPI_PROFILE_NAME\",' \
                                ' \"description\": \"KPI_PROFILE_DESCRIPTION\",' \
                                ' \"kpis\": [ KPI_STRUCTURE ]}'
        kpi_structure = '{ \"kpi_id\": \"KPI_ID\", \"cadence\": 60, \"alerting\": true }'

        KPI_PROFILE_STRUCTURE = KPI_PROFILE_STRUCTURE.replace("KPI_PROFILE_NAME", "system")
        KPI_PROFILE_STRUCTURE = KPI_PROFILE_STRUCTURE.replace("KPI_PROFILE_DESCRIPTION",
                                                              "system KPIs")
        #kpi_list = [ "pulse_cpu_utilization", "pulse_memory_utilization" ]   
        cw_kpis = ast.literal_eval(self.crosswork_kpis)                                             
        kpi_input_list = ""
        #for kpi in list(set(kpi_list)):
        for kpi in cw_kpis:
            kpi_input_list += kpi_structure
            kpi_input_list = kpi_input_list.replace("KPI_ID", kpi)
            kpi_input_list += ","
        kpi_input_list = kpi_input_list[:-1]
        print("LIST self.crosswork_klpi_list  ", self.crosswork_kpis)
        print("type self.crosswork_klpi_lis  ", type(self.crosswork_kpis))

        KPI_PROFILE_STRUCTURE = \
            KPI_PROFILE_STRUCTURE.replace("KPI_STRUCTURE", kpi_input_list)
        logger.info('KPI_PROFILE_STRUCTURE  ::  %s', KPI_PROFILE_STRUCTURE)

        url = "https://" + self.crosswork_ip_address + ":" + str(
            self.crosswork_port) + "/crosswork/hi/v1/kpiprofilemgmt/write"
        headers = {'Content-Type': "application/json",
                   'Authorization': "Bearer " + self.get_token(),
                   'Cache-control': "no-cache",
                   }
        response = ""
        response = (requests.request("POST",
                                     url,
                                     data=KPI_PROFILE_STRUCTURE,
                                     headers=headers,
                                     verify=False))
        logger.info('create_kpi_profile: return code ::  %s', response.text)


        logger.info('enableKpis() : enable Kpis')
        url = "https://" \
              + self.crosswork_ip_address \
              + ":" \
              + str(self.crosswork_port) \
              + "/crosswork/hi/v1/kpiprofileassoc/write"
        headers = {'Content-Type': "application/json",
                   'Authorization': "Bearer " + self.get_token()}

        return response

    def enable_kpi_profile(self):
        logger.info('enableKpis() : enable Kpis')
        url = "https://" \
            + self.crosswork_ip_address \
            + ":" \
            + str(self.crosswork_port) \
            + "/crosswork/hi/v1/kpiprofileassoc/write"
        headers = {'Content-Type': "application/json",
                'Authorization': "Bearer " + self.get_token()}
        device_list = self.get_devices_list()
        logger.info('kpi_profile_payload  2 -0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-::  %s', device_list)
        logger.info('TYPE kpi_profile_payload  2 -0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-::  %s', type(device_list))
        kpi_profile_name = 'system'
        kpi_profile_payload_nodes ='{"devices": device_list, "kpi_profiles":[kpi_profile_name]}'
        kpi_profile_payload_nodes.replace("device_list", str(device_list))
        kpi_profile_payload_nodes.replace("kpi_profile_name", 'system')
        logger.info('*****************kpi_profile_payload ::  %s', kpi_profile_payload_nodes)
        #kpi_profile_payload ='{"devices": ["Node-1", "Node-2"], "kpi_profiles":["system"]}'
        kpi_profile_payload ='{"devices": device_list, "kpi_profiles":["system"]}'
        kpi_profile_payload = kpi_profile_payload.replace("device_list", str(device_list).replace("\'", "\""))
        # new code
        #kpi_profile_payload ='{"devices": ["Node-1", "Node-2"], "kpi_profiles":["system"]}'
        # end of new code
        logger.info('kpi_profile_payload ::  %s', kpi_profile_payload)

        response = ""
        response = (requests.request("POST",
                                    url,
                                    data=kpi_profile_payload,
                                    headers=headers,
                                    verify=False))
        logger.info('enableKpis(): return code ::  %s', response.text)

        return response

# ---------------------------------------------
# Auto enables kpis based on the NSO service
# ---------------------------------------------
def main():
    cw = Crosswork()
    cw.create_kpi_profile()
    result = cw.enable_kpi_profile()
    logger.info('enableKpis() : return code ::  %s', result.text)


if __name__== "__main__":
    main()  
