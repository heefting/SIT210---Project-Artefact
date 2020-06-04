import requests

# Takes in values and trigger event name
def ifttt_alert(trigger_name,first, second, third):
    '''
    Sends IFTTT alerts using the trigger and key for IFTTT webhooks
    '''
    report = {}
    report["value1"] = first
    report["value2"] = second
    report["value3"] = third
    # Your webhook api key here
    secret_key = 'your key here'
    requests.post('https://maker.ifttt.com/trigger/{}/with/key/{}'.format(trigger_name,secret_key),data=report)

# --
