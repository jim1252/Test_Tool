#!/usr/bin/env python3
'''
File:           settings_tool.py
Brief:          Send a series of commands to a STB to provide correct settings
Author:         James McArthur
Contributors:   N/A

Copyright
---------
Copyright 2009-2024 Commscope Inc. All rights reserved.
This program is confidential and proprietary to Commscope Inc.
(CommScope), and may not be copied, reproduced, modified, disclosed to
others, published or used, in whole or in part, without the express
prior written permission of CommScope.
'''

import paramiko
import argparse
import sys
import os
import json
from datetime import datetime
import ipaddress
import time

port =22
username ='root'
password = ' '
ip = ' '
connectedSTB = ' ' 
ssh = paramiko.SSHClient()
noSetting = 'Error:key'
url_reporting = 'https://8uc2224o95.execute-api.eu-west-2.amazonaws.com/default/reportingIon'
server = ' '
updateProfile = ' '
updateAlpha = ' '
updateWatermark = ' '
updateAutoTime = ' '
memTotal = ' '
audioDelay = ("0", "10", "20", "30", "40","50", "60", "70", "80", "90","100", "110", "120", "130", "140","150", "160", "170", "180", "190", "200")
audioAtt = ("0dB", "-3dB", "-6dB", "-9dB", "-11dB",)
playbackType = ("download", "stream")
audio = ("Dolby", "Stereo")
classificationAge = ("0", "5", "6", "7", "8", "9",)

stbDetails = {} # Create Dictionary for STB details
stbPrimary = {} # Create Dictionary for Primary Settings
defaultSettings = {} # Create Dictionary for Tempoary/Default Settings to be stored
mySTBs = {} # Create Dictionary for nested STB dictionaries

class stb:
    def __init__(self, CDSN, saved):
        self.CDSN = CDSN
        self.saved = saved
        
    def savedState(self):
        print('STB: ' + self.CDSN + ' - Settings saved: ' + self.saved)

s1 = stb('00000000', 'false')

def get_args():
    reporting_parser = argparse.ArgumentParser(description='To set the reporting settings on a STB', epilog='for additional help contact James McArthur')
    #reporting_parser.add_argument('required', action='store_true', help='IP Address of the STB to Update (Required)')
    reporting_parser.add_argument('-ip', help='IP Address of the STB to Update, -ip ipaddr')
    reporting_parser.add_argument('-rf_connection', action='store_true',
                                  help="simulate disconnection of RF feed.  ")
    reporting_parser.add_argument('-erlang_Connect', action='store_true',
                                  help='Connect to XMPP Erlang server (For access to Pidgin, XMPP remote) the STB reboots after commands have been sent.  If build is very old and script does not run because of new additions this should connect STB to Erlang server regardless')
    reporting_parser.add_argument('-reboot', action='store_true', help='Reboots STB')
    reporting_parser.add_argument('-read', action='store_true', help="return values for all reporting settings")
    reporting_parser.add_argument('-details', action='store_true', help="returns STB details; CDSN Serial number, mode")
    #reporting_parser.add_argument('-options', action='store_true',
                                  #help='Opens a menu to individually set the main reporting settings')
    reporting_parser.add_argument('--debug', action='store_true', help='Debug Printing')
   
    return reporting_parser.parse_args()
    print(vars(args))

def sshConnection(ip): #Create SSH connection to STB
    args = get_args()
    if args.debug:
        print ('Using paramiko to create SSH shell')
    print('calling paramiko')
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print ('Trying to connect to', ip)
    ssh.connect(ip, port, username, password)
    print ('Connected to', ip)

def close(): #To end the SSH connection 
    ssh.close()
    print ('Connection Closed')

def getCDSN(): # Gets the STB's CDSN and sets it global as CDSN
    cdsn_cmd ='calljs "pace.CA.getSerialNumber(1)"'
    sshSendCommand(cdsn_cmd)
    if len(lines) > 1 and lines[1]:
        cdsn_resp = lines[1]
        cdsn_resp1 = cdsn_resp.replace('   string ""', '')
        global CDSN
        CDSN = cdsn_resp1.rstrip('""\n')
        print ('CDSN: ' + CDSN)
    else:
        print ("'===ERROR RETURNING SERIAL NUMBER==='\n'" + ' try rebooting STB and try again' )
        close()

def sshSendCommand(command): 
    stdin, stdout, stderr = ssh.exec_command(command, timeout=10)
    stdin.close()
    args = get_args()
    if args.debug:
        print ('command sent,  Stdout is variable lines err is variable err')
    global lines
    lines = stdout.readlines()
    global err
    err = stderr.readlines()

def sshCmd(command): #Send command to STB no confirmation no STB response required
    try:
        sshSendCommand(command)
        print ('Command Sent:  ' + command)
        return True

    except Exception as e:
        print("Connection lost : %s" %e)
        print('trying to reconnect')
        args = get_args()
        ip = args.ip
        sshConnection(ip)
        sshSendCommand(command)
        print ('Command Sent:  ' + command)
        return False
    
def readSettings(command): # Send comand and print setting with a lot of the extra characters removed for ease of reading
    global stbReadSetting
    #stbSetting = ()
    global saveSetting
    try:
        args = get_args()
        sshSendCommand(command)
        settingsRead = lines[0]
        settingsRead = settingsRead.replace('OK:key', '')
        stbReadSetting = settingsRead.rstrip(' \r\n')
        print(stbReadSetting)
        saveSetting = stbReadSetting.rstrip('"\n')
        if args.debug:
            print('Setting: ' + saveSetting)
        return True

    except Exception as e:
        print("Connection lost : %s" %e)
        print('trying to reconnect')
        args = get_args()
        ip = args.ip
        sshConnection(ip)
        print ('sending Command')
        sshSendCommand(command)
        settingsRead = lines[0]
        settingsRead = settingsRead.replace('OK:key', '')
        stbReadSetting = settingsRead.rstrip(' \r\n')
        print(stbReadSetting)
        saveSetting = stbReadSetting.rstrip('\n')
        return False

def sshSettingsCommand(command): #Send a settings command to STB and return stdout only
    #global lines
    try:
        print ('sending Command: ' + command)
        sshSendCommand(command)
        print(*lines)
        return True

    except Exception as e:
        print("Connection lost : %s" %e)
        print('trying to reconnect')
        args = get_args()
        ip = args.ip
        sshConnection(ip)
        sshSendCommand(command)
        print ('sending Command: ' + command)
        print(*lines)
        return False

def sshSQLCommand(command): #Send SQL commands to STB and return stdout printing results on seperate lines
                            #Timout - if timeout is breached, 5 seconds, it considereds the connection to be lost
                            #and attempts to reconnect to STB followed by sending the command 
    try:
        sshSendCommand(command)
        print(*lines)
        return True

    except Exception as e:
        print("Connection lost : %s" %e)
        print('trying to reconnect')
        args = get_args()
        ip = args.ip
        sshConnection(ip)
        sshSendCommand(command)
        print(*lines)
        return False

def sshRespCommand(command, debug): #Send command to STB confirmation only no command sent shown
    
    try:
        if debug == True:
            print ('sending Command: ' + command)
        sshSendCommand(command)
        print(*lines)
        return True

    except Exception as e:
        print("Connection lost : %s" %e)
        print('trying to reconnect')
        args = get_args()
        ip = args.ip
        sshConnection(ip)
        sshSendCommand(command)
        print(*lines)
        return False

def getSTBdetails():
    global stbPrimary
    stbPrimary = {} # Create Dictionary for Primary Settings    
    args = get_args()
    getCDSN() 
    connectedSTB = (CDSN)
    stbDetails.update({"CDSN": CDSN}) #add CDSN to stbDetail dictionary    
    stbPrimary.update({"CDSN": CDSN})  # add CDSN to stbPrimary dictionary
    model_type()    
    stbDetails.update({"iQ": box_type}) #
    stbPrimary.update({"iQ": box_type})
    stbDetails.update({"IP": ip}) #add IP to stbDetail dictionary
    stbPrimary.update({"IP": ip})  # add IP to stbPrimary dictionary
    getSerialNumber()
    stbDetails.update({"serial Number": serialNumber}) # add serial number to stbDetail dictionary
    stbPrimary.update({"serial Number": serialNumber})
    
    if args.debug:
        print (connectedSTB)
    
    if mySTBs.get(connectedSTB) is not None: # if the STB is in mySTBS extract STB settings too stbPrimary
        s1.saved = "true"
        print(f"The STB {connectedSTB} is in the file.")
        if args.debug:
            print('test see if I can extract dictionary \n', mySTBs[connectedSTB])
        stbPrimary = mySTBs[connectedSTB]
        
        if args.debug:
            print ('test what is in stbPrimary \n', stbPrimary)
    else: 
        print(f"The STB {connectedSTB} is not the file.") # if the STB is not in mySTBS - user input
        try:
            while True:
                print ("This STB has no saved settings")
                confirm = input('Do you want to save the current settings for this STB Y/N : ')
                    
                if confirm == 'Y':
                    #print('User selected yes, still in development no actions taken')
                    writeToFile()
                    s1.CDSN = stbDetails['CDSN']
                    s1.saved = "true"
                    s1.savedState()
                    break
                    
                elif confirm == 'N':
                    print('User selected No, Getting information from STB')
                    break                        
                                
                else:
                    print('Invalid entry please try again:')
                    continue
                        
        except KeyboardInterrupt:
            print('CTRL+C Pressed. ')
                            
    SoftwareDetails()
    stbDetails.update({"software Version": softwareVer}) # add software version to stbDetail dictionary
    stbPrimary.update({"software Version": softwareVer})
    stbDetails.update({"build Number": buildVer}) # add software build number to stbDetail dictionary
    stbPrimary.update({"build Number": buildVer})
    getMode()
    stbDetails.update({"STB Mode": stbMode}) #add mode to stbDetail dictionary
    stbPrimary.update({"STB Mode": stbMode})
       
    s1.CDSN = stbDetails['CDSN']
        
    if args.debug:
        print('stbPrimary Dictionary', stbPrimary)
    #mySTBs[CDSN] = stbPrimary # needs changing overwrites everything
    
def model_type(): # get model type from the STB
    sshSendCommand('calljs "pace.config.getOemModelId()"')
    global box_type
    if len(lines) > 1 and lines[1]:
        mt_resp = lines[1]
        mt_resp1 = mt_resp.replace('   string ""', '')
        modelType = mt_resp1.rstrip('""\n')
        #print ('Model Type: ' + modelType)
        
        if modelType in ["0A", "2A"]:
            box_type = "iQ4"
            print('STB Type: ' + box_type)
            
        elif modelType in ["09", "89"]:
            box_type = "iQ3"
            print('STB Type: ' + box_type)
            
        elif modelType in ["0B", "2B"]:
            box_type = "iQ5"
            print('STB Type: ' + box_type)
    else:
        print ("'===ERROR RETURNING Model Type==='\n'" + ' try rebooting STB and try again' )
        close()

def getSerialNumber():
    get_serial_cmd ='dbus-send --system --type=method_call --print-reply --dest=org.pace.s_man /s_man org.pace.s_man.get_serialisation_element_as_string string:"STB_SERIAL_NUMBER" '
    sshSendCommand(get_serial_cmd)
    stbSerialN = lines[1]
    stbSerialN = stbSerialN.replace('   string "', '')
    global serialNumber
    serialNumber = stbSerialN.rstrip('""\n')
    print('Serial Number:' + serialNumber)
        
def getVersion(): #Get STB current software version
    get_version_cmd ='calljs "pace.config.softwareVersion()" '
    sshSendCommand(get_version_cmd)
    stbSoftwareV = lines[1]
    stbSoftwareV = stbSoftwareV.replace('  string ""', '')
    global softwareVer
    softwareVer = stbSoftwareV.rstrip('""\n')
        
def getBuild():
    get_build_cmd ='calljs "pace.config.firmwareVersion()" '
    sshSendCommand(get_build_cmd)
    stbBuild = lines[1]
    stbBuild = stbBuild.replace('  string ""', '')
    global buildVer
    buildVer = stbBuild.rstrip('""\n')
        
def SoftwareDetails():
    getVersion()
    getBuild()
    print('Software Version:' + softwareVer + '    Build Version:' + buildVer)

def stbMacAddr(): # gets the STB's ethernet MAC address and sets it global as macaddr
    ifconfig ='/sbin/ifconfig'
    stdin, stdout, stderr = ssh.exec_command(ifconfig)
    stdin.close()
    stderr.close()
    global lines
    lines = stdout.readlines()
    eth0 = lines[0]
    macaddr1 = eth0.replace('eth0      Link encap:Ethernet  HWaddr ', '')
    global macaddr
    macaddr = macaddr1.rstrip(' \r\n')
    print ('MAC Address: ' + macaddr)

def getMode():
    stdin, stdout, stderr = ssh.exec_command('settings_cli get "tungsten.ux.DeliveryMode" ')
    print ('Sending Command: settings_cli get "tungsten.ux.DeliveryMode" ')
    stdin.close()
    stderr.close()
    global lines
    lines = stdout.readlines()
    settingsRead = lines[0]
    settingsRead = settingsRead.replace('OK:key "tungsten.ux.DeliveryMode" , "', '')
    global stbMode
    stbMode = settingsRead.rstrip('" \r\n')   
    print ('STB mode: ' + stbMode)

def changeMode(): # To change the STB's mode between IP and DSMCC
    getMode()
    confirm = input('Current STB mode is ' + stbMode + ' Are you sure want to continue enter Y : ')
                    
    if confirm == 'Y':
        try:
            while True:     
                modes = ("http", "dsmcc")
                modeChoosen = str(input('Enter required mode: http or dsmcc: '))
                if modeChoosen in modes:
                #if modeChoosen == modes[0] or modeChoosen == modes[1]:
                    print(modeChoosen + ' Selected')
                    command = 'settings_cli Set "tungsten.ux.DeliveryMode" '
                    global stbModeCommand
                    stbModeCommand = command + modeChoosen
                    sshSettingsCommand(stbModeCommand)
                    #locationReload()
                    sshCmd('/sbin/reboot -d 5') #reboots the STB after a 5 second delay
                    print('rebooting STB')
                    close() # Closes SSH
                    sys.exit(0)
                                                            
                else:
                    print('Mode not recognised. Try again')
                continue
                                        
        except KeyboardInterrupt:
            print('CTRL+C Pressed')        
                
    else:
        print('Canceled')

def sshResolution(command): #Send command to STB to get the current screen resolution
    stdin, stdout, stderr = ssh.exec_command(command, timeout=5)
    stdin, stdout, stderr = ssh.exec_command(command)
    stdin.close()
    stderr.close()
    global lines
    lines = stdout.readlines()
    lines = lines.pop(9)
    lines = lines.rstrip('\n')
    print(lines)
    return True
def killApp(application):
    getpid = f'echo `pidof {application}`'
    readSettings(getpid)
    print(application + ' pid ' + stbReadSetting[:5])
    sshCmd(f'kill -9 {stbReadSetting[:5]}')
    readSettings(getpid)

def reportingSetup():
    print('Will set STB to standard reporting settings to ensure reporting works.\n  If alternate settings are required set them in the command line.  Use --H in command line for help on available settings') 
    confirm = input('Do you wish to continue? enter Y : ')
                    
    if confirm == 'Y':
        args = get_args()
        uri = "https://8uc2224o95.execute-api.eu-west-2.amazonaws.com/default/reportingIon"
        reportingEnable = 'True'
        reporting_time = 0
        config = 0 
        #server_URL(uri)
        reporting_enable(reportingEnable) # turn reporting on or off (True/False)
        reportingDelay(reporting_time) # set value reporting update delay
        appConfigReportDelay(config) # set value for app config delay
        print('Sending commands to STB')
        sshSettingsCommand('server')
        sshSettingsCommand(enableCommand)
        sshSettingsCommand(reportingDelay)
        sshSettingsCommand(appConfigDelay)
                    
    else:
        print('Reporting setup canceled')

def reportingDelay(reporting_time):
    if reporting_time:
        print('reporting time Set')
        reportingTime = reporting_time

    else:
        reportingTime = input('Enter Reporting time delay(default 3600): ')

    timeStr = str(reportingTime)
    command = 'settings_cli Set "tungsten.ams.updateDelay" '
    global reportDelay
    reportDelay = command + timeStr
    print (reportDelay)
                         
def appConfigReportDelay(config): #Set Application Configuration, user input
    if config:
        print('config set')
        timeDelay = config

    else:
        timeDelay = input ('Enter Application Configuration time delay(default 86400): ')

    timeDelayStr = str(timeDelay)
    configCommand = 'settings_cli Set "tungsten.reporting_service.appConfigReportDelay" '
    global appConfigDelay
    appConfigDelay = configCommand + timeDelayStr
    print (appConfigDelay)

def reporting_enable(enable):
    enableStr = str(enable)
    command = 'settings_cli Set "tungsten.ams.enabled" '
    global enableCommand
    enableCommand = command + enableStr
    print (enableCommand)

def server_URL(url):
    reportingUrl = 0
    if url:
        print('URL Set')
        reportingURL = url

    else:
        reportingUrl = (input('Enter required URL, leave blank to set default: "https://8uc2224o95.execute-api.eu-west-2.amazonaws.com/default/reportingIon": ')
                                                or "https://8uc2224o95.execute-api.eu-west-2.amazonaws.com/default/reportingIon")

    urd = str(reportingUrl)
    command = 'settings_cli set "tungsten.reporting_service.uri" '
    global server
    server = command + urd
    print(server)

def AmsID(ams):
    if ams:
        print('updateDelay time set')

    else:
        ams = input('Enter AmsID: ')

    command = 'settings_cli Set "tungsten.ams.AmsID" '
    global AmsID
    AmsID = command + ams
    print(AmsID)

def rf_feed():
    sshConnection(ip)
    print('Simulate RF feed Disconnect') 
    confirm = input('Enter Y to disconnect RF, anything else to reconnct RF: ')
                    
    if confirm == 'Y':
        sshSettingsCommand('calljs "pace.test.simulateDisconnectedFeed(true)"')
        print('RF Feeds Disconnected')
        
    else:
        sshSettingsCommand('calljs "pace.test.simulateDisconnectedFeed(false)"')
        print('RF Feeds Connected')

    print('Close Connection')
    close() # Close connection to the STB

def settingsRead():
    print('Read Settings')
    readSettings('settings_cli get "tungsten.ux.DeliveryMode" ')
    ss1 = saveSetting.replace('"tungsten.ux.DeliveryMode" , "', '')
    stbPrimary.update({"STB Mode": ss1})  # add STB auto Standby Time to stbPrimary dictionary
    readSettings('settings_cli get tungsten.ux.autoStandbyTimeout')
    ss1 = saveSetting.replace('"tungsten.ux.autoStandbyTimeout" , "', '')
    stbPrimary.update({"autoStandbyTimeout": ss1})  # add STB auto Standby Time to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.ams.enabled"')
    ss1 = saveSetting.replace('"tungsten.ams.enabled" , "', '')
    stbPrimary.update({"reportingEnabled": ss1})  # add STB ams/reporting enabled to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.ams.updateDelay" ')
    ss1 = saveSetting.replace('"tungsten.ams.updateDelay" , "', '')
    stbPrimary.update({"updateDelay": ss1})  # add Reporting message delay to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.reporting_service.appConfigReportDelay" ')
    ss1 = saveSetting.replace('"tungsten.reporting_service.appConfigReportDelay" , "', '')
    stbPrimary.update({"appConfigReportDelay": ss1})  # add Reporting Config delay to stbPrimary dictionary
    readSettings('settings_cli get tungsten.reporting_service.uri')
    ss1 = saveSetting.replace('"tungsten.reporting_service.uri" , "', '')
    stbPrimary.update({"reportinguri": ss1})  # add reporting uri to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.reporting_service.sendEventsToLocalFileOnly" ')
    ss1 = saveSetting.replace('"tungsten.reporting_service.sendEventsToLocalFileOnly" , "', '')
    stbPrimary.update({"sendEventsToLocalFileOnly": ss1})  # EventsToLocalFileOnly to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.ams.numEventsInBundle" ')
    ss1 = saveSetting.replace('"tungsten.ams.numEventsInBundle" , "', '')
    stbPrimary.update({"ams.numEventsInBundle": ss1})  # add reportingEventsInBundle to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.ams.cacheSize" ')
    ss1 = saveSetting.replace('"tungsten.ams.cacheSize" , "', '')
    stbPrimary.update({"ams.CacheSize": ss1})  # add reportingCacheSize to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.ams.AmsID"')
    ss1 = saveSetting.replace('"tungsten.ams.AmsID" , "', '')
    stbPrimary.update({"AmsID": ss1})  # add AmsID to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.watermark.profile"')
    ss1 = saveSetting.replace('"tungsten.watermark.profile" , "', '')
    stbPrimary.update({"watermark.profile": ss1})  # add STB waterwmark profile to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.watermark.alpha"')
    ss1 = saveSetting.replace('"tungsten.watermark.alpha" , "', '')
    stbPrimary.update({"watermark.alpha": ss1})  # add STB watermark alpha to stbPrimary dictionary
    readSettings('settings_cli Get "tungsten.watermark.enabled"')
    ss1 = saveSetting.replace('"tungsten.watermark.enabled" , "', '')
    stbPrimary.update({"watermark.enabled": ss1})  # add STB auto Standby Time to stbPrimary dictionary
    readSettings('settings_cli get "tungsten.ux.audioSettingsFormatSpdif"')
    ss1 = saveSetting.replace('"tungsten.ux.audioSettingsFormatSpdif" , "', '')
    stbPrimary.update({"audioSettingsFormatSpdif": ss1})
    readSettings('settings_cli get "tungsten.ux.audioSettingsFormatHdmi"')
    ss1 = saveSetting.replace('"tungsten.ux.audioSettingsFormatHdmi" , "', '')
    stbPrimary.update({"audioSettingsFormatHdmi": ss1})
    readSettings('settings_cli get "tungsten.ux.digitalAudioLevel"')
    ss1 = saveSetting.replace('"tungsten.ux.digitalAudioLevel" , "', '')
    stbPrimary.update({"digitalAudioLevel": ss1})
    readSettings('settings_cli get "tungsten.ux.digitalAudioLevelHdmi"')
    ss1 = saveSetting.replace('"tungsten.ux.digitalAudioLevelHdmi" , "', '')
    stbPrimary.update({"digitalAudioLevelHdmi": ss1})
    readSettings('settings_cli get "tungsten.ux.audioDelay"')
    ss1 = saveSetting.replace('"tungsten.ux.audioDelay" , "', '')
    stbPrimary.update({"audioDelay": ss1})
    readSettings('settings_cli get "tungsten.ux.audioDelayHdmi"')
    ss1 = saveSetting.replace('"tungsten.ux.audioDelayHdmi" , "', '')
    stbPrimary.update({"audioDelayHdmi": ss1})
    readSettings('settings_cli get "tungsten.ux.parentalRating"')
    ss1 = saveSetting.replace('"tungsten.ux.parentalRating" , "', '')
    stbPrimary.update({"parentalRating": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_PICTURE_RATING"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PICTURE_RATING" , "', '')
    stbPrimary.update({"UI_SETTING_PICTURE_RATING": ss1})
    readSettings('settings_cli Get "tungsten.ux.nonRatedPC"')
    ss1 = saveSetting.replace('"tungsten.ux.nonRatedPC" , "', '')
    stbPrimary.update({"nonRatedPC": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_PIN_PURCHASE"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PIN_PURCHASE" , "', '')
    stbPrimary.update({"UI_SETTING_PIN_PURCHASE": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_PIN_KEPT_PROGRAMS"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PIN_KEPT_PROGRAMS" , "', '')
    stbPrimary.update({"UI_SETTING_PIN_KEPT_PROGRAMS": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_PIN_IP_VIDEO"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PIN_IP_VIDEO" , "', '')
    stbPrimary.update({"UI_SETTING_PIN_IP_VIDEO": ss1})
    readSettings('settings_cli get "tungsten.ux.ParentalPincode"')
    ss1 = saveSetting.replace('"tungsten.ux.ParentalPincode" , "', '')
    stbPrimary.update({"ParentalPincode": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_BANDWIDTH_QUALITY"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_BANDWIDTH_QUALITY" , "', '')
    stbPrimary.update({"UI_SETTING_BANDWIDTH_QUALITY": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_POSTCARDS_ENABLED"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_POSTCARDS_ENABLED" , "', '')
    stbPrimary.update({"UI_SETTING_POSTCARDS_ENABLED": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_DOWNLOAD_QUALITY"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_DOWNLOAD_QUALITY" , "', '')
    stbPrimary.update({"UI_SETTING_DOWNLOAD_QUALITY": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_PPV_PLAYBACK_TYPE"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PPV_PLAYBACK_TYPE" , "', '')
    stbPrimary.update({"UI_SETTING_PPV_PLAYBACK_TYPE": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_ON_DEMAND_PLAYBACK_TYPE"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_ON_DEMAND_PLAYBACK_TYPE" , "', '')
    stbPrimary.update({"UI_SETTING_ON_DEMAND_PLAYBACK_TYPE": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_BUFFER_SIZE"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_BUFFER_SIZE" , "', '')
    stbPrimary.update({"UI_SETTING_BUFFER_SIZE": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_VOICE_ENABLED"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_VOICE_ENABLED" , "', '')
    stbPrimary.update({"UI_SETTING_VOICE_ENABLED": ss1})
    readSettings('settings_cli get "tungsten.ux.hdmiCecControlSetting"')
    ss1 = saveSetting.replace('"tungsten.ux.hdmiCecControlSetting" , "', '')
    stbPrimary.update({"hdmiCecControlSetting": ss1})
    readSettings('settings_cli get "tungsten.ux.hdmiCecVolumeControlSetting"')
    ss1 = saveSetting.replace('"tungsten.ux.hdmiCecVolumeControlSetting" , "', '')
    stbPrimary.update({"hdmiCecVolumeControlSetting": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_YOUBORA_SYSTEM"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_YOUBORA_SYSTEM" , "', '')
    stbPrimary.update({"YOUBORA_SYSTEM": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_SCREENSAVER_ENABLED"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_SCREENSAVER_ENABLED" , "', '')
    stbPrimary.update({"screenSaverEnabled": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_TIMEOUT_LENGTH"')
    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_TIMEOUT_LENGTH" , "', '')
    stbPrimary.update({"screenSaverTimeout": ss1})
    readSettings('settings_cli get "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH"')
    ss1 = saveSetting.replace(' "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH" , "', '')
    stbPrimary.update({"screenSaverPath": ss1})

def rebootHard():
    sshCmd('/sbin/reboot -d 5') #reboots the STB after a 5 second delay
    print('rebooting STB')
    close() # Closes SSH
    sys.exit(0) #Exit Settings script

def stbReboot():
    if s1.saved == 'true':
        print ('stb is saved')
        updateMySTB()
        writemySTBsFile()

    else:
        writemySTBsFile()

    sshCmd('/sbin/reboot -d 5') #reboots the STB after a 5 second delay
    print('rebooting STB')
    close() # Closes SSH
    sys.exit(0) #Exit Settings script

def locationReload():
    sshCmd('calljs "location.reload()"')


def autoWrite(): #if STB has been saved current settings are automatically written to file
    s1.savedState()
    if s1.saved == 'true':
        print ('stb is saved')
        updateMySTB()
        writemySTBsFile()

    else:
        print('STB settings have not been saved')

def writeDetailsFile(): #writes STB deatils to a text file called stbDetails
    with open ('stbDetails.txt', 'w', encoding='UTF-8') as f: # Opens file
        for key, value in stbDetails.items(): # stbDetails - dictionary containing info
            f.write('%s:%s\n' % (key, value)) #writes each key on a new line in text file
    #detailsFile.close() #Close file
        
def writemySTBsFile(): # writes mySTBs dictionary to mySTBs.json
    with open('mySTBs.json', 'w', encoding='UTF-8') as write_file:
        json.dump(mySTBs, write_file)

def readmySTBsFile():  #read mySTBs json file shows user the settings values and updates dict mySTBs
    args = get_args()
    try:
        with open("mySTBs.json", "r", encoding='UTF-8') as read_file:
            mySTBs.update (json.load(read_file))
            if args.debug:
                print('STB details read from file /n', mySTBs)
            
    except FileNotFoundError: # only used if file has not yet been created
        print('User settings file has not yet been created, please create one by running writing settings to file')


def writeToFile(): # read user settings save in dict and write to file
    args = get_args()
   
    if s1.saved == 'false':
        print ('stb is not saved, reading settings to write to file')
        settingsRead()

    updateMySTB() # Current stbPrimary dict updated in mySTBS so it can be written to file
    if args.debug:
        print('stbPrimary Dictionary', stbPrimary)
        #print('mySTBs dictionary', mySTBs)
    writemySTBsFile() # Write all STB info to file - mySTBs
    s1.saved = "true"
    if args.debug:
        s1.savedState()
  
def updateMySTB(): # Current stbPrimary dict updated in mySTBS so it can be written to file 
    args = get_args()
    CDSN = stbPrimary['CDSN']
    if args.debug:
        print ('Original mySTBs Dictionary: \n', mySTBs)
        print ('current stbPrimary Dictionary: \n', stbPrimary)    
        print ('CDSN from stbPrimary', CDSN)
    mySTBs[CDSN] = stbPrimary
    if args.debug:
        print ('updated mySTBs Dictionary: \n', mySTBs)
    print ('mySTBs have been updated')

def writeDefaultFile(): #writes user settings from dict stbPrimary to json file stbSettings.json
    defaultSettings = dict(stbPrimary)
    defaultSettings.pop("CDSN")
    with open('stbDefault.json', 'w', encoding='UTF-8') as write_file:
        json.dump(defaultSettings, write_file)
        
def readDefaultFile():  #read settings json file shows user the settings values and updates dict stbPrimary
    args = get_args()
    try:
        with open("stbDefault.json", "r", encoding='UTF-8') as read_file:
            defaultSettings.update (json.load(read_file))
            if args.debug:
                print ('default settings Dictionary', defaultSettings)
                
    except FileNotFoundError: # only used if file has not yet been created
        print('User settings file has not yet been created, please create one by running writing settings to file')

def updateUserSettings(): # uses settings dict stbPrimary and sends them to the STB
    print (defaultSettings)
    primarySet = defaultSettings['updateDelay']
    sshCmd("""settings_cli set "tungsten.ams.updateDelay"%s """ % primarySet)
    primarySet = defaultSettings['appConfigReportDelay']
    sshCmd("""settings_cli set "tungsten.reporting_service.appConfigReportDelay"%s """ % primarySet)
    primarySet = defaultSettings['autoStandbyTimeout']
    sshCmd("""settings_cli set "tungsten.ux.autoStandbyTimeout"%s """ % primarySet)
    primarySet = defaultSettings['reportingEnabled']
    sshCmd("""settings_cli set "tungsten.ams.enabled"%s """ % primarySet)
    primarySet = defaultSettings['reportinguri']
    sshCmd("""settings_cli set "tungsten.reporting_service.uri"%s """ % primarySet)
    primarySet = defaultSettings['watermark.profile']
    sshCmd("""settings_cli set "tungsten.watermark.profile"%s """ % primarySet)
    primarySet = defaultSettings['watermark.alpha']
    sshCmd("""settings_cli set "tungsten.watermark.alpha"%s """ % primarySet)
    primarySet = defaultSettings['watermark.enabled']
    sshCmd("""settings_cli set "tungsten.watermark.enabled"%s """ % primarySet)
    primarySet = defaultSettings['ParentalPincode']
    sshCmd("""settings_cli set "tungsten.ux.ParentalPincode"%s """ % primarySet)
  
def sendErlangSetup():
    print('Sending commands to set STB to ejabbered Server')
    erlangSQLite()
    command = """sqlite3 /mnt/ffs/settings/active.db 'update active_table set value = "trustedJids=remotedvr@cobalt.pace.com,remotedvr@elements-dev.xyz,remotedvr@xmpp.connectedhomesolutions.net,remotedvr@elements.commscope.com,scripts@elements-dev.xyz,human@elements-dev.xyz,automation2.0@elements-dev.xyz,remotedvr@xmpp.connectedhomesolutions.net,automation2.0@xmpp.connectedhomesolutions.net,scripts@xmpp.connectedhomesolutions.net,human@xmpp.connectedhomesolutions.net,foxtel_automation@managed.dev-xmpp.foxtel.com.au,foxtel_automation@xmpp.thomasholtdrive.com", modified = "true" where key = "tungsten.provisioning.xmppConfiguration";' """
    sshCmd(erlangSQLite)
    sshCmd(command)
    sshCmd('settings_cli Set "application.mainapp.AUTOMATION_2_0_ENABLED" true')
    sshCmd('settings_cli Set "application.mainapp.AUTOMATION_2_0_XMPP_DESTINATION" COMMSCOPE_A2.0')
    sshCmd('/sbin/reboot -d 2') #reboots the STB after a 2 second delay
    print('Commands sent to STB to connect to Erlang Server')

def erlangSQLite():
    start = "sqlite3 /mnt/ffs/settings/active.db 'UPDATE active_table set value="
    end = "'"
    global erlangSQLite
    erlangSQLite = start + '"description=server,user=' + CDSN + '.iq3,password=' + CDSN + \
                   '.iq3,domain=xmpp.connectedhomesolutions.net,resource=iq3,auth=digest" where ' \
                   'key like "tungsten.provisioning.xmpp1" '+ end
    print (erlangSQLite)

def main():
    print('main running')
    readmySTBsFile()
    readDefaultFile()
    args = get_args()
    
    myIPs = []
    print("STB's already saved")
    for x, obj in mySTBs.items():
        print(x, 'IP: ', end=" ")
        print(mySTBs[x]['IP'])
        myIPs.append(mySTBs[x]['IP'])
        if args.debug:
            print(myIPs)

    args = get_args()
    global ip

    if args.ip is None:
        print('IP not set at arg parse')
        
        while True:
            try:
                value = input('Enter IP of STB: ')
                if ipaddress.ip_address(value):
                    print("Valid IP address")
                    break

            except ValueError:
                # If the input is not a valid IP Address, cvatch the exception and print an error message
                print("Invalid IP address")
                continue    
        
        ip = value

    else:
        
        ip = args.ip
        if args.debug:
            print ('Global IP set as: ', ip)
    details = args.details
    read = args.read
    reboot = args.reboot
    rf_connection = args.rf_connection
    erlang_Connect = args.erlang_Connect
    print('STB IP =', ip)
            
    if reboot == 1:
        sshConnection(ip)
        rebootHard()
    
    elif read == 1:
        print('read settings')
        sshConnection(ip)
        settingsRead()
        close()
        
    elif details == 1:  
        sshConnection(ip)
        getSTBdetails()
                
    elif rf_connection == 1:
        print('RF Connected')
        rf_feed()
        
    elif erlang_Connect == 1:
        sshConnection(ip)
        getCDSN()
        sendErlangSetup()
        sys.exit(0)

    else:
        print('open')
        #readmySTBsFile()
        #readDefaultFile()
        sshConnection(ip)
        getSTBdetails()
        readSettings('settings_cli get "tungsten.standby.rebootCountSinceFSR"')
        rebootFSR = saveSetting.replace('"tungsten.standby.rebootCountSinceFSR" , "', '')
        if args.debug:
            print('reboots since FSR: ' + rebootFSR)
        if stbPrimary.get('rebootCountSinceFSR') is None:
            print ('No FSR count')
        #print(stbPrimary['rebootCountSinceFSR'])
        elif rebootFSR < stbPrimary['rebootCountSinceFSR']:
            try:
                while True:
                    print ("STB has been FSR'd recently")
                    confirm = input('Do you want to update STB from saved settings Y/N : ')
                    
                    if confirm == 'Y':
                        print('Updating user settings from file')
                        updateUserSettings()
                        stbPrimary.update({"rebootCountSinceFSR": rebootFSR})
                        updateMySTB()
                        writemySTBsFile()
                        break
                    
                    elif confirm == 'N':
                        print('User selected no.')
                        break                        
                                
                    else:
                        print('Invalid selection')
                        continue
                        
            except KeyboardInterrupt:
                print('CTRL+C Pressed. Shutting Down')
                close()
                
        if ip != stbPrimary['IP']:
            try:
                while True:
                    print ("The IP for this STB does not match")
                    confirm = input('Do you want to update STB from saved settings Y/N : ')
                    
                    if confirm == 'Y':
                        print('Updating user settings from file')
                        updateUserSettings()
                        stbPrimary.update({"IP": ip})
                        updateMySTB()
                        writemySTBsFile()
                        break
                    
                    elif confirm == 'N':
                        print('User selected no, IP for this STB has been updated')
                        stbPrimary.update({"IP": ip})
                        break                        
                                
                    else:
                        print('Invalid selection')
                        continue
                        
            except KeyboardInterrupt:
                print('CTRL+C Pressed. Shutting Down')
                close()
            
        stbPrimary.update({"rebootCountSinceFSR": rebootFSR})
        print('Version:', stbPrimary["software Version"])
               
        if args.debug:
            debug = True
            
        else:
            debug = False 
        deb = f"{': '} {debug}"
        print ('Is Debug on', deb)        
        writeDetailsFile()
        
        try:
            while True:
                print('\n CDSN: ' + stbDetails["CDSN"] + '   IP addr: ' + stbDetails["IP"] + '   Software Version:' + stbDetails["software Version"])
                options =  """    
                Select a setting to change: \n
                *** Main Settings ***
                   0 - SQL Queries
                   1 - Search STB Settings
                   2 - Send SSH command, typed in full
                   3 - Set Auto Standby Time
                   4 - Simulate RF Disconnect
                   5 - Change STB Mode IP\Hybrid
                   6 - Connect to XMPP Erlang server (Pidgin, XMPP remote)
                   7 - FSR - Full System Reset
                   8 - Screen Resolution for streaming assets, 8c for continuous                   
                   10 - YouBora Server Connection
                   11 - Reset Keep stream as default message  
                   12 - View bookablePromos available \n
                   20 - Tester Settings\n                
                   30 - Developer Settings\n
                   40 - User Settings\n                 
                   50 - System Information \n 
                   r - Reboot STB
                   s - Save Settings
                   q - quit \n
                  """
                print(options)
                x = input('>: ')

                if x == '0':
                    try:
                        while True:
                            options =  """\n      Select a SQL query to run:  \n 
                 1 - Future events
                 2 - Past Events
                 3 - Events by Start Time
                 4 - Series linked events for current/future events
                 5 - Series linked events for past events
                 6 - Rebroadcast times for past events
                 7 - Rebroadcast times for future events
                 8 - Event with no rebroadcasting scheduled search by channel
                 9 - Events with no rebroadcast scheduled  search by Start Time
                 10 - Find single/individual TV show assets, no series or episode number
                 11 - TV series missing meta-data, shows 100 current and future events
                 12 - Series Link Events   
                 13 - STB Library Searches
                 14 - List Foxtel EPG channels
                 15 - Where Next event parental rating > current event
                 16 - Where Next event parental rating < current event
                 17 - Future instances of rise in parental rating on change of event
                 18 - Future instances of fall in parental rating on change of event
                 19 - Current event with StartOver and following event without StartOver
                 20 - Current event without StartOver and following event with StartOver
                 21 - Future events with Startover and event following that without Startover
                 22 - Future events without Startover and event following that with Startover
                 23 - Team Link Events
                 24 - Main Events
                 25 - Age restricted content on now
                 
                 30 - Custom Field with channel filter
                 
                 b - back               
                 q - quit \n    """
                             
                            print(options)
                            x = input('>: ')

                            if x == '1':
                                channel = input('Enter channel number: ')
                                limit = input('Enter number of event to return: ')
                                print('Future event info for channel:' + channel)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '     Programme Title    ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Key ', c.value as 'Channel', a.startover,a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime limit %s" """"" % (channel,limit))
                                continue

                            elif x == '2':
                                channel = input('Enter channel number: ')
                                print('Past event info for channel:' + channel)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '   Programme Title  ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover,a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start, 'unixepoch', 'localtime') < datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime desc limit 100" """"" % channel)
                                continue

                            elif x == '3':
                                now = datetime.now()
                                date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
                                print('Current DateTime:', date_time_str, ' - this is your current datetime you will need to adjust for the correct time in Sydney \n')
                                time1 = input('Enter the lower range for Starttime in "YYYY-MM-DD HH:MM:SS" format: ')
                                time2 = input('Enter the upper range for Starttime in "YYYY-MM-DD HH:MM:SS" format: ')
                                print('Events by Start Time')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum,a.EvName as '      Programme Title     ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover,a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and c.key='ChannelTag'and StartTime>'%s' and StartTime<'%s'order by StartTime limit 100" """"" % (time1,time2))
                                continue

                            elif x == '4':
                                channel = input('Enter channel number: ')
                                print('Events info for channel:' + channel)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '       Programme Title       ',a.series_Id as 'Series Id',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now','localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime limit 50" """"" % channel)
                                serid = input('Enter the Series Id from above : ')
                                print('All episodes from the selected Series')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select EvName as '      Programme Title       ', datetime(Start,'unixepoch', 'localtime') as starttime, datetime(start + duration, 'unixepoch', 'localtime') as Endtime, episode_title, contentProviderID, uniqueContentID, series_Id, episode_seasonId as Season, episode_episodeId as Episode from event_list where series_Id='%s'"; """"" % serid)
                                continue

                            elif x == '5':
                                channel = input('Enter channel number: ')
                                print('Events info for channel:' + channel)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '     Programme Title       ', a.series_Id, datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start, 'unixepoch', 'localtime') < datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime desc limit 50" """"" % channel)
                                serid = input('Enter the Series Id from above : ')
                                print('All episodes from the selected Series')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select EvName as '        Programme Title       ', datetime(Start,'unixepoch', 'localtime') as starttime, datetime(start + duration, 'unixepoch', 'localtime') as Endtime, episode_title, contentProviderID, uniqueContentID, series_Id, episode_seasonId as Season, episode_episodeId as Episode from event_list where series_Id='%s'"; """"" % serid)
                                continue

                            elif x == '6':
                                channel = input('Enter channel number: ')
                                order = input('Enter enter list order asc or desc: ')
                                print('Past events info for channel:' + channel)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '      Programme Title      ', a.uniqueContentID,datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover,a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start, 'unixepoch', 'localtime') < datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime %s limit 50" """"" % (channel, order))
                                ucid = input('Enter the Assets UCID from above : ')
                                print('All episodes of the selected Asset: ' + ucid)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '      Programme Title      ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID,  a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', b.ChanNum as 'Channel',a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where c.key='ChannelTag'and a.uniqueContentID='%s' order by StartTime asc limit 50" """"" % ucid)
                                continue

                            elif x == '7':
                                channel = input('Enter channel number: ')
                                print('Events information for channel:' + channel)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '      Programme Title      ', a.uniqueContentID,datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover,a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now','localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime limit 50" """"" % channel)
                                ucid = input('Enter the Assets UCID from above : ')
                                print('All episodes of the selected Asset: ' + ucid)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '      Programme Title      ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID,  a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', b.ChanNum as 'Channel Number',a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where c.key='ChannelTag'and a.uniqueContentID='%s' order by StartTime asc limit 50" """"" % ucid)
                                continue

                            elif x == '8':
                                print('Channels with no series and episode numbers')
                                sshSQLCommand("""sqlite3 /tmp/cache.db "select group_concat(ChanNum, ',') from (select distinct(b.ChanNum) from event_list a inner join service_list b on a.ContentID_Service=b.ContentID_Service where episode_seasonId is null and episode_episodeId is null and a.genre is not 4 and a.genre is not 1024 order by b.ChanNum)" """)
                                cont = "y"
                                while(cont == "y"):
                                    channel = input('Enter channel number: ')
                                    print('Event with no rebroadcast scheduled by channel')
                                    sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '     Programme Title       ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID,b.ChanNum as 'Channel Number',a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) group by uniqueContentID having count(uniqueContentID)<=1 and datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and b.ChanNum=%s order by StartTime limit 100" """ % channel)
                                    cont = input('Do you want to run this query for other channel : ')
                                continue

                            elif x == '9':
                                now = datetime.now()
                                date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
                                print('Current DateTime:', date_time_str, ' - this is your current datetime you will need to adjust for the correct time in Sydney \n')
                                time1 = input('Enter the lower range for Starttime, events that start after this time, in "YYYY-MM-DD HH:MM:SS" format: ')
                                time2 = input('Enter the upper range for Endtime, events that finish before this time,  in "YYYY-MM-DD HH:MM:SS" format: ')
                                print('Events with no rebroadcast by Start Time')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '       Programme Title       ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID,b.ChanNum as 'Channel Number',a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) group by uniqueContentID having count(uniqueContentID)<=1 and StartTime>'%s' and Endtime<'%s'order by StartTime limit 100" """"" % (time1,time2))
                                continue

                            elif x == '10':
                                print('Channels with no series and episode numbers')
                                sshSQLCommand("""sqlite3 /tmp/cache.db "select group_concat(ChanNum, ',') from (select distinct(b.ChanNum) from event_list a inner join service_list b on a.ContentID_Service=b.ContentID_Service where episode_seasonId is null and episode_episodeId is null and a.genre is not 4 and a.genre is not 1024 order by b.ChanNum)" """)
                                cont = "y"
                                while(cont == "y"):
                                    channel = input('Enter channel number: ')
                                    print('Assets with no series and episode number')
                                    sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "Select datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.EvName, a.contentProviderID , b.ChanNum, b.ServiceName from event_list a inner join service_list b on a.ContentID_Service=b.ContentID_Service where episode_episodeId is null and episode_seasonId is null and a.genre is not 4 and a.genre is not 1024 and b.ChanNum=%s order by StartTime" """ % channel)
                                    cont = input('Do you want to run this query for other channel : ')
                                continue

                            elif x == '11': # Series link Searches
                                try:
                                    while True:
                                        options = """\n      Series link SQL searches     \n                            
                 1 - No Episode Title incomplete Series/Episode
                 2 - No Episode Title has complete Series/Episode information
                 3 - Has Episode title incomplete Series/Episode1 - Find available series on specific channel number
                 q - quit
                 b - back                 """
                                        print(options)
                                        x = input('>: ')

                                        if x == '1':
                                            print('No Episode Title incomplete Series/Episode. Episode number is shown as without it only Single TV show assets would be inluded')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "Select datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.EvName, a.episode_title, a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode, a.contentProviderID , b.ChanNum from event_list a inner join service_list b on a.ContentID_Service=b.ContentID_Service where episode_title is null and episode_seasonId is null and series_Id is not null and a.genre is not 4 and a.genre is not 1024 and datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') order by StartTime limit 100" """)
                                            continue

                                        elif x == '2':
                                            print('No Episode Title has complete Series/Episode information')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "Select datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.EvName, a.episode_title, a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode, a.contentProviderID , b.ChanNum from event_list a inner join service_list b on a.ContentID_Service=b.ContentID_Service where episode_title is null and series_Id is not null and a.genre is not 4 and a.genre is not 1024 and datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') order by StartTime limit 100" """)
                                            continue

                                        elif x == '3':
                                            print('Episode title, incomplete Series/Episode')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "Select datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.EvName, a.episode_title, a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode, a.contentProviderID , b.ChanNum from event_list a inner join service_list b on a.ContentID_Service=b.ContentID_Service where episode_seasonId is null and a.genre is not 4 and a.genre is not 1024 and datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and a.episode_title is not null order by StartTime limit 100" """)
                                            continue
  
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()



                            elif x == '12': # Series link Searches
                                try:
                                    while True:
                                        options = """\n      Series link SQL searches     \n                            
                 1 - Find available series on specific channel number
                 2 - Search for available series for event Title
                 3 - Search for available Episodes for event Title
                 4 - Search For all assets for specific SeriesID
                 5 - Air times for first Episodes in a series
                 q - quit
                 b - back                 """
                                        print(options)
                                        x = input('>: ')

                                        if x == '1':
                                            channel = input('Enter channel number: ')
                                            limit = input('Enter number of event to return: ')
                                            print('Series information for channel:' + channel)
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName, datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.uniqueContentID,  a.episode_seasonId as season, a. episode_episodeId as episode, a.Series_Id, c.value as 'Channel Tag', b.ChanNum from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId) where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime limit %s" """"" % (channel,limit))
                                            #sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as '     Programme Title    ',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Key ', c.value as 'Channel', a.startover,a.series_Id, a.episode_seasonId as Season, a.episode_episodeId as Episode from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=%s order by StartTime limit %s" """"" % (channel,limit))
                                            continue
                                                                        
                                        elif x == '2':
                                            print('This uses a wildcard serach, to find an asset like "Blue Bloods", the search terms; blue, bloods, lue bl, will all find the asset "Blue Bloods" ')
                                            title = input('Enter the assets title, : ')
                                            print('Series information search on:' + title)
                                            sshSQLCommand(f"""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select count (distinct a.episode_episodeId) as episodes, a.EvName as Program_Title         , a.Series_Id, a.episode_seasonId as season, b.ChanNum, c.RelatedServiceType as Type from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join related_channel_list c on (a.ContentID_Service=c.RelatedChannelId) group by EvName, series_Id, episode_seasonId having series_Id is not null and a.episode_seasonNumber < 101 and EvName LIKE '%{title}%' and datetime(a.start, 'unixepoch', 'localtime') > datetime('now', 'localtime') limit 100" """)
                                            continue
                                        
                                        elif x == '3':
                                            print('This uses a wildcard serach, to find an asset like "Blue Bloods", the search terms; blue, bloods, lue bl, will all find the asset "Blue Bloods" ')
                                            title = input('Enter the assets title, : ')
                                            print('Episode information search on:' + title)
                                            sshSQLCommand(f"""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName, datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.uniqueContentID,  a.episode_seasonId as season, a. episode_episodeId as episode, a.Series_Id, b.Service_key as 'Service Key', c.value as 'Channel Tag', b.ChanNum from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId) where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and EvName LIKE '%{title}%' and c.key='ChannelTag' order by series_Id limit 100" """)
                                            continue

                                        elif x == '4':
                                            print('This will show all episodes of a particular SeriesID')
                                            seriesId = input('Enter the SeriesId : ')
                                            print('SeriesID to search with:' + seriesId)
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName, datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.episode_seasonId as season, a. episode_episodeId as episode, a.Series_Id,  b.ChanNum from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) where series_Id = '%s' order by StartTime limit 100" """"" % (seriesId))
                                            continue

                                        elif x == '5':
                                            print('Air times for first episode in series ')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select datetime(a.start, 'unixepoch', 'localtime') as StartTime, a.episode_seasonId as Season, a.episode_episodeNumber as Episode, a.EvName as 'Program Title          ', a.Series_Id, c.value as 'Channel Tag', b.ChanNum from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId) where episode_episodeNumber = '1' and episode_seasonId is not null and series_Id is not null and c.key='ChannelTag' and StartTime >= datetime('now','localtime') order by StartTime Asc limit 100" """ )
                                            continue
                                            
                                        elif x == '6':
                                            print('5')  
                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()


                            elif x == '13': # HDD Library searches
                                try:
                                    while True:
                                        options = """\n      Library searches     \n                            
                 1 - PVR Library Recorded
                 2 - VOD Library Downloaded
                 3 - Series assets in Library
                 4 - SeriesId search
                 q - quit
                 b - back                 """
                                        print(options)
                                        x = input('>: ')

                                        if x == '1':
                                            print('Library PVR Recorded')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "attach '/tmp/cache.db' as db1; attach '/mnt/hd/meta/record.db' as db2; select a.ContentID_Recording,a.evname as '  Programme Title  ', a.episode_title as 'Episode title', datetime(Start,'unixepoch', 'localtime') as 'Recorded at', f.ServiceName as ' Channel Name ', e.value as 'Channel Source', a.series_Id, a.IsSeriesLinked, duration as 'Ev Dur(sec)', actual_duration as 'Rec Dur(sec)',  b.reached_playback_position as 'Watched Dur', a.tungsten_leadtime as 'Lead Time', a.tungsten_lagtime as 'Lag Time' from db1.recorded_event_list a inner join db2.recording b on (a.ContentID_Recording=b.id) inner join db1.RecordedEventCustomFields c on (a.ContentID_Recording=c.recordingId) inner join db1.ServiceCustomFields e on (a.ContentID_Service=e.serviceId) inner join db1.service_list f on (a.ContentID_Service=f.ContentID_Service) where c.key='TitleID' and e.key='ChannelSource'"  """)
                                            continue

                                        elif x == '2':
                                            print('Library VOD Recorded')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "attach '/tmp/cache.db' as db1; attach '/mnt/hd/meta/record.db' as db2; select distinct(ContentID_Recording), a.evname as '  Programme Title  ',a.series_Id,time(duration, 'unixepoch') as 'Asset Duration', time(actual_duration, 'unixepoch') as 'Watched Duration', d.value as 'Source Type', c.value as type from db1.recorded_event_list a inner join db2.recording b on (a.ContentID_Recording=b.id) inner join db1.RecordedEventCustomFields c on (a.ContentID_Recording=c.recordingId) inner join db1.RecordedEventCustomFields d on (a.ContentID_Recording=c.recordingId) where c.key='sourceType' and d.key='type'"  """)
                                            continue

                                        elif x == '3':
                                            print('Series assets in Library')
                                            sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName, a.series_Id, a.episode_seasonId as season, a.episode_episodeId as episode, a.contentProviderId, datetime(a.Start,'unixepoch', 'localtime') as 'Recorded at', c.value as Tag, b.ChanNum from recorded_event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId) where series_Id is not null and c.key='ChannelTag' order by series_Id" """ )
                                            continue
                                            
                                                            
                                        elif x == '4':
                                            print('This uses a wildcard search, to find all assets containing the entered seriesID.  You only need to enter part of the seriesID ')
                                            seriesId = input('Enter the SeriesId : ')
                                            print('SeriesID to search with:' + seriesId)
                                            sshSQLCommand(f"""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName, a.series_Id, a.episode_seasonId as season, a.episode_episodeId as episode, a.contentProviderId, datetime(a.Start,'unixepoch', 'localtime') as 'Recorded at', c.value as Tag, b.ChanNum from recorded_event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId) where series_Id like '%{seriesId}%' and c.key='ChannelTag' " """)
                                            continue  
                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()

                            elif x == '14':
                                print('List all EPG channels')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select distinct a.ContentID_Service, a.ServiceName, a.brand as 'Channel_Brand_Name', a.ChanNum, b.value as Tag from service_list a inner join ServiceCustomFields b on (a.ContentID_Service=b.serviceId) where b.key='ChannelTag' order by ChanNum asc" """)

                            elif x == '15':
                                print('Where Next event parental rating > current event')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum,b.ServiceName,c.EvName as 'Event',(case when c.Parental='4' then 'G' when c.Parental='5' then 'PG' when c.Parental='6' then 'M' when c.Parental='7' then 'MA15+' when c.Parental='9' then 'R18' END) as Rating,datetime(c.start,'unixepoch','localtime') as StartTime,a.EvName as '   Next Event   ',(case when a.Parental='4' then 'G' when a.Parental='5' then 'PG' when a.Parental='6' then 'M' when a.Parental='7' then 'MA15+' when a.Parental='9' then 'R18' END) as Rating,datetime(a.start,'unixepoch','localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join event_list a on (a.start=(c.start+c.duration) and a.ContentID_Service=c.ContentID_Service) where datetime(c.start,'unixepoch','localtime')<datetime('now','localtime') and datetime(c.start+c.duration,'unixepoch','localtime')>=datetime('now','localtime') and a.parental>c.Parental and b.ChanNum is not 0 order by b.ChanNum asc;" """)
                                continue

                            elif x == '16':
                                print('Where Next event parental rating < current event')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum,b.ServiceName,c.EvName as 'Event',(case when c.Parental='4' then 'G' when c.Parental='5' then 'PG' when c.Parental='6' then 'M' when c.Parental='7' then 'MA15+' when c.Parental='9' then 'R18' END) as Rating,datetime(c.start,'unixepoch','localtime') as StartTime,a.EvName as '   Next Event   ',(case when a.Parental='4' then 'G' when a.Parental='5' then 'PG' when a.Parental='6' then 'M' when a.Parental='7' then 'MA15+' when a.Parental='9' then 'R18' END) as Rating,datetime(a.start,'unixepoch','localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join event_list a on (a.start=(c.start+c.duration) and a.ContentID_Service=c.ContentID_Service) where datetime(c.start,'unixepoch','localtime')<datetime('now','localtime') and datetime(c.start+c.duration,'unixepoch','localtime')>=datetime('now','localtime') and a.parental<c.Parental and b.ChanNum is not 0 order by b.ChanNum asc" """)
                                continue

                            elif x == '17':
                                print('Future instances of rise in parental rating on change of event')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum,b.ServiceName,c.EvName,(case when c.Parental='4' then 'G' when c.Parental='5' then 'PG' when c.Parental='6' then 'M' when c.Parental='7' then 'MA15+' when c.Parental='9' then 'R18' END) as Rating,datetime(c.start,'unixepoch','localtime') as StartTime,a.EvName as 'Following Event',(case when a.Parental='4' then 'G' when a.Parental='5' then 'PG' when a.Parental='6' then 'M' when a.Parental='7' then 'MA15+' when a.Parental='9' then 'R18' END) as Rating,datetime(a.start,'unixepoch','localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join event_list a on (a.start=(c.start+c.duration) and a.ContentID_Service=c.ContentID_Service) where datetime(c.start,'unixepoch','localtime')<datetime(date('now','+1 day'),'localtime') and datetime(c.start+c.duration,'unixepoch','localtime')>=datetime('now','localtime') and a.parental>c.Parental and b.ChanNum is not 0 order by b.ChanNum asc" """)
                                continue

                            elif x == '18':
                                print('Future instances of fall in parental rating on change of event')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum,b.ServiceName,c.EvName,(case when c.Parental='4' then 'G' when c.Parental='5' then 'PG' when c.Parental='6' then 'M' when c.Parental='7' then 'MA15+' when c.Parental='9' then 'R18' END) as Rating,datetime(c.start,'unixepoch','localtime') as StartTime,a.EvName as 'Following Event',(case when a.Parental='4' then 'G' when a.Parental='5' then 'PG' when a.Parental='6' then 'M' when a.Parental='7' then 'MA15+' when a.Parental='9' then 'R18' END) as Rating,datetime(a.start,'unixepoch','localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join event_list a on (a.start=(c.start+c.duration) and a.ContentID_Service=c.ContentID_Service) where datetime(c.start,'unixepoch','localtime')<datetime(date('now','+1 day'),'localtime') and datetime(c.start+c.duration,'unixepoch','localtime')>=datetime('now','localtime') and c.parental>a.Parental and b.ChanNum is not 0 order by b.ChanNum asc" """)
                                continue

                            elif x == '19':
                                print('Current event with StartOver and following event without StartOver')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum, b.ServiceName, c.EvName as 'Current Event', c.contentProviderID, c.startover, datetime(c.start, 'unixepoch', 'localtime') as StartTime, a.EvName as 'Next Event', a.contentProviderID, a.startover, datetime(a.start, 'unixepoch', 'localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service = b.ContentID_Service) inner join event_list a on (a.start = (c.start + c.duration) and a.ContentID_Service = c.ContentID_Service) where datetime(c.start, 'unixepoch', 'localtime') < datetime('now', 'localtime') and datetime(c.start + c.duration, 'unixepoch', 'localtime') >= datetime('now','localtime') and a.startover = 'false' and c.startover = 'true' and b.ChanNum is not 0 order by b.ChanNum asc;" """)
                                continue

                            elif x == '20':
                                print('Current event without StartOver and following event with StartOver')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum, b.ServiceName, c.EvName as 'Current Event', c.contentProviderID, c.startover, datetime(c.start, 'unixepoch', 'localtime') as StartTime, a.EvName as 'Next Event', a.contentProviderID, a.startover, datetime(a.start, 'unixepoch', 'localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service = b.ContentID_Service) inner join event_list a on (a.start = (c.start + c.duration) and a.ContentID_Service = c.ContentID_Service) where datetime(c.start, 'unixepoch', 'localtime') < datetime('now', 'localtime') and datetime(c.start + c.duration, 'unixepoch', 'localtime') >= datetime('now','localtime') and c.startover = 'false' and a.startover = 'true' and b.ChanNum is not 0 order by b.ChanNum asc;" """)
                                continue

                            elif x == '21':
                                print('Future events with Startover and event following that without Startover')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum, b.ServiceName, c.EvName as 'Event', c.contentProviderID, c.startover, datetime(c.start, 'unixepoch', 'localtime') as StartTime, a.EvName as 'Following Event', a.contentProviderID, a.startover, datetime(a.start, 'unixepoch', 'localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service = b.ContentID_Service) inner join event_list a on (a.start = (c.start + c.duration) and a.ContentID_Service = c.ContentID_Service) where datetime(c.start, 'unixepoch', 'localtime') < datetime(date('now', '+1 day'), 'localtime') and datetime(c.start + c.duration, 'unixepoch', 'localtime') >= datetime('now','localtime') and a.startover = 'false' and c.startover = 'true' and b.ChanNum is not 0 order by b.ChanNum asc;" """)
                                continue

                            elif x == '22':
                                print('Future events without Startover and event following that with Startover')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select b.ChanNum, b.ServiceName, c.EvName as 'Event', c.contentProviderID, c.startover, datetime(c.start, 'unixepoch', 'localtime') as StartTime, a.EvName as 'Following Event', a.contentProviderID, a.startover, datetime(a.start, 'unixepoch', 'localtime') as StartTime from event_list c inner join service_list b on (a.ContentID_Service = b.ContentID_Service) inner join event_list a on (a.start = (c.start + c.duration) and a.ContentID_Service = c.ContentID_Service) where datetime(c.start, 'unixepoch', 'localtime') < datetime(date('now', '+1 day'), 'localtime') and datetime(c.start + c.duration, 'unixepoch', 'localtime') >= datetime('now','localtime') and a.startover = 'true' and c.startover = 'false' and b.ChanNum is not 0 order by b.ChanNum asc;" """)
                                continue

                            elif x == '23':
                                print('Team Link')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select distinct ChanNum, ServiceName, EvName, datetime(Start, 'unixepoch', 'localtime') from event_list inner join eventIds_teamLinkIds on event_list.ContentID_Event=eventIds_teamLinkIds.eventId inner join service_list on event_list.ContentID_Service=service_list.ContentID_Service order by Start" """)
                                continue
                            elif x == '24':
                                print('Main Event')
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as 'Programme Title',datetime(a.start, 'unixepoch', 'localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as Endtime, a.ppv_price, a.ppv_rentalperiod, a.ppv_serviceid, a.contentProviderID, a.uniqueContentID, b.Service_key as 'Service Key', c.value as 'Channel Tag', a.startover from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) inner join ServiceCustomFields c on (a.ContentID_Service=c.serviceId)where datetime(a.start + a.duration, 'unixepoch', 'localtime')> datetime('now', 'localtime') and c.key='ChannelTag'and b.ChanNum=521 and a.ppv_serviceid is not NULL order by StartTime limit 50"  """)
                                continue

                            elif x == '25':
                                print('STB age Codes \n 4 = G \n 5 = PG \n 6 = M \n 7 = MA15+ \n 9 = R18')
                                rating = input('Enter Required age code: ')
                                print ('Assets that are on Now for: ' + rating)
                                sshSQLCommand("""sqlite3 -column -header -separator $'\t' /tmp/cache.db "select a.EvName as 'Program_Title       ', (case when a.Parental='4' then 'G' when a.Parental='5' then 'PG' when a.Parental='6' then 'M' when a.Parental='7' then 'MA15+' when a.Parental='9' then 'R18' END) as Rating, b.ChanNum, datetime(a.start,'unixepoch','localtime') as StartTime, datetime(a.start + a.duration, 'unixepoch', 'localtime') as EndTime from event_list a inner join service_list b on (a.ContentID_Service=b.ContentID_Service) where StartTime < Endtime and datetime('now', 'localtime') between StartTime And EndTime and a.Parental = '%s' order by ChanNum;" """"" % rating)
                                continue

                            elif x == '30':
                                custom = input('Enter Custom field search criteria "TV_NO_EPS" "MOVIE": ')
                                channel1 = input('Enter Enter Lower channel number: ')
                                channel2 = input('Enter Enter Lower channel number, enter previous channel number to search on single channel: ')
                                channel_range = (channel1 + ' and ' + channel2)
                                print (channel_range)
                                print (custom)
                                command = (f"""sqlite3 /tmp/cache.db "Select b.ChanNum,  a.EvName, datetime(a.start, 'unixepoch', 'localtime') as StartTime from event_list a inner join service_list b on (a.ContentID_Service = b.ContentID_Service) where datetime(a.start + a.duration, 'unixepoch', 'localtime') > datetime('now', 'localtime') and customFields like '%{custom}%' AND ChanNum between {channel_range} order by StartTime LIMIT 25;"  """)
                                print (command)
                                sshSQLCommand(command)
                                continue

                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))
                            continue

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()

                if x == '1':
                    userInput = input ('Enter Text such as; Netflix, watermark, audio, PIN, to return all results containing the searched text. \n  Enter text to search STB settings: ')
                    print(userInput)
                    sshSettingsCommand(f'settings_cli getall | grep {userInput}')
                
                elif x ==  '2':
                    print('Type full command to be sent to STB: ')
                    userInput = input ('Enter Text such as; Netflix, watermark, audio, PIN, to return all results containing the searched text. \n  Enter text to search STB settings: ')
                    print(userInput)
                    sshSettingsCommand(userInput)
                
                elif x == '3':
                    try:
                        while True:
                            print('current Auto Standby time is: ')
                            readSettings('settings_cli get tungsten.ux.autoStandbyTimeout')
                            ss1 = saveSetting.replace('"tungsten.ux.autoStandbyTimeout" , "', '')
                            stbPrimary.update({"autoStandbyTimeout": ss1})  # add STB auto Standby Time to stbPrimary dictionary
                            enter = input('Enter Auto Standby time (Default 14400): ')
                            autoTime = str(enter) #autoTime new time to set STB to
                            readSettings('settings_cli Get "tungsten.ux.autoStandbyWarning"')
                            ss1 = saveSetting.replace('"tungsten.ux.autoStandbyWarning" , "', '')
                            stbPrimary.update({"autoStandbyWarning": ss1})  # add Standby warning to stbPrimary dictionary
                            if autoTime != '60':
                                print ('time' + autoTime)
                                sshSettingsCommand('settings_cli set tungsten.ux.autoStandbyWarning "60"')
                            command = 'settings_cli set "tungsten.ux.autoStandbyTimeout"  '
                            global updateAutoTime
                            updateAutoTime = command + autoTime
                            print(updateAutoTime)
                            sshSettingsCommand(updateAutoTime)
                            readSettings('settings_cli get tungsten.ux.autoStandbyTimeout')
                            ss1 = saveSetting.replace('"tungsten.ux.autoStandbyTimeout" , "', '')
                            stbPrimary.update({"autoStandbyTimeout": ss1})  # add STB auto Standby Time to stbPrimary dictionary
                            break
                    except KeyboardInterrupt:
                        continue
                
                elif x == '4': # Change RF Feed connection
                    try:
                        while True:
                            options = """\n      Simulate RF Disconnection     \n                            
                 1 - Disconnect 
                 2 - Connect
                 q - quit
                 b - back                 """
                            print(options)
                            x = input('>: ')

                            if x== '1':
                                sshSettingsCommand('calljs "pace.test.simulateDisconnectedFeed(true)"')
                                print('RF Feeds Disconnected')
                                
                            elif x == '2':
                                sshSettingsCommand('calljs "pace.test.simulateDisconnectedFeed(false)"')
                                print('RF Feeds Connected')
                                
                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))
                            continue

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()
                
                elif x == '5': # Switch mode between IP and dsmcc
                    changeMode() 
                
                elif x == '6': #Connect to XMPP server(Erlang)
                    getCDSN()
                    sendErlangSetup()
                    sys.exit(0) 
                
                elif x == '7': #FSR
                    confirm = input('Are you sure want to perform a Full system reset on your STB? To continue enter Y : ')
                    
                    if confirm == 'Y':
                        sshCmd('touch /mnt/ffs/reset')
                        sshCmd('sync')
                        stbReboot()
                                
                    else:
                        print('FSR canceled')
                        continue
                
                elif x == '8': # Get screen resolution
                    print('Screen Resolution: ')
                    sshResolution('cat /proc/brcm/video_decoder')
                    continue
                
                elif x == '8c': # Get screen resolution continuous
                    print('Screen Resolution: \n Press CTRL-C to stop')
                    try:
                        while True:
                            sshResolution('cat /proc/brcm/video_decoder')
                            time.sleep(5)
                            continue
                            
                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()
                                    
                
                                
                elif x == '10': # Connection to YouBora Server
                    try:
                        while True:
                            options = """\n      Connection to youBora server     \n                            
                 1 - Check current YouBora server setting
                 2 - Connect to foxsportsaustralia
                 3 - Connect to foxteldev
                 q - quit
                 b - back                 """
                            print(options)
                            x = input('>: ')

                            if x == '1':
                                readSettings('settings_cli get "application.mainapp.UI_SETTING_YOUBORA_SYSTEM"')
                                ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_YOUBORA_SYSTEM" , "', '')
                                stbPrimary.update({"YOUBORA_SYSTEM": ss1})
                                                            
                            elif x == '2':
                                sshSettingsCommand('settings_cli set "application.mainapp.UI_SETTING_YOUBORA_SYSTEM" foxsportsaustralia')
                                readSettings('settings_cli get "application.mainapp.UI_SETTING_YOUBORA_SYSTEM"')
                                ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_YOUBORA_SYSTEM" , "', '')
                                stbPrimary.update({"YOUBORA_SYSTEM": ss1})
                                #print('Disconnecting from PTS')
                                #stbReboot() # is this needed
                            
                            elif x == '3':
                                sshSettingsCommand('settings_cli set "application.mainapp.UI_SETTING_YOUBORA_SYSTEM" foxteldev')
                                readSettings('settings_cli get "application.mainapp.UI_SETTING_YOUBORA_SYSTEM"')
                                ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_YOUBORA_SYSTEM" , "', '')
                                stbPrimary.update({"YOUBORA_SYSTEM": ss1})
                                #print('Disconnecting from PTS')
                                #stbReboot() # is this needed    
                            
                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))
                            continue

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()
                
                elif x == '11':
                    sshSettingsCommand('settings_cli set "application.mainapp.UI_SETTING_OD_PLAYBACK_TYPE_DIALOG_SHOWN" "FALSE"')
                    stbReboot()

                elif x == '12':
                    sshSettingsCommand('ls -l /tmp/bookablePromos')
                
                elif x == '20':
                    try:
                        while True:
                            options = """
                    *** Tester Settings ***
                  21 - Application tools 
                  22 - Reporting Settings
                  23 - Watermark Settings
                  24 - Low memory Values
                  25 - Time management Priorities 
                  26 - Screensaver settings
                  27 - STB default settings
                  b - back
                  q - quit\n 
                  """
                            print(options)
                            x = input('>: ')

                            if x == '21':
                                try:
                                    while True:
                                        options = """\n    Application Tools \n                            
                             1 - Get Application PIDS 
                             2 - Status Netflix
                             3 - Status Amazon
                             4 - Status WPE Browser, FTA, Paramount+ 
                             5 - Status Disney
                             6 - Status YouTube
                             7 - Kill Netflix 
                             8 - Kill Amazon
                             9 - Kill WPE Browser, FTA, Paramount+ 
                             10 - Kill Disney Plus
                             11 - Kill YouTube
                             20 - Memory allocation tool
                             21 - Netflix DRM 
                             r - reboot
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '1':
                                            print('Netflix PID:')
                                            readSettings('echo `pidof netflix`')
                                            
                                            print('Amazon PID:')
                                            readSettings('echo `pidof ignition`')
                                            
                                            print('WPE Browser, FTA Paramount+ PID:')
                                            readSettings('echo `pidof cog`')
                                            
                                            print('Disney Plus PID:')
                                            readSettings('echo `pidof merlin`')
                                            
                                            print('YouTube:')
                                            readSettings('echo `pidof loader_app`')
                                            
                                        elif x == '2':
                                            sshSettingsCommand('ps aux | grep Netflix')
                                            
                                        elif x == '3':
                                            sshSettingsCommand('ps aux | grep [i]gnition')
                                            
                                        elif x == '4':
                                            sshSettingsCommand('ps aux | grep [c]og')
                                            
                                        elif x == '5':
                                            sshSettingsCommand('ps aux | grep -i [d]isneyplus')
                                            
                                        elif x == '6':
                                            sshSettingsCommand(' ps aux | grep [c]obalt')
                                            
                                        elif x == '7':
                                            killApp('netflix')
                                            
                                        elif x == '8':
                                            killApp('ignition')
                                            
                                        elif x == '9':
                                            killApp('cog')
                                            
                                        elif x == '10':
                                            killApp('merlin')
                                            
                                        elif x == '11':
                                            killApp('loader_app')
                                            
                                        elif x == '20':
                                            global memTotal
                                            memTotal = int(0)
                                            os.system('cls')
                                            try:
                                                while True:
                                                    options = """   Memory Setter \n                            
                                 1 - Allocate Memory
                                 2 - Free up Memory
                                 r - Reboot STB
                                 b - back
                                 """
                                                    print(options)
                                                    print('Total memory Allocated: ' + str(memTotal))
                                                    x = input('>: ')
                                                    
                                                    if x== '1':
                                                        memValue = int(input('Enter value of memory to allocate : '))
                                                        memTotal = memTotal + memValue
                                                        print('Total memory Allocated: ' + str(memTotal))                                            
                                                        commanda = '/usr/bin/allocateAndFreeMemory.sh a '
                                                        updateMem = commanda + str(memValue)
                                                        print(updateMem)
                                                        sshCmd(updateMem)
                                                        os.system('cls')
                                                        
                                                    elif x == '2':
                                                        memValue = int(input('Enter value of memory to free up : '))
                                                        memTotal = memTotal - memValue
                                                        print('Total memory Allocated: ' + str(memTotal))
                                                        commandf = '/usr/bin/allocateAndFreeMemory.sh f '
                                                        updateMem = commandf + str(memValue)
                                                        print(updateMem)
                                                        sshCmd(updateMem)
                                                        os.system('cls')
                                                        
                                                    elif x == 'r':
                                                        stbReboot()
                                                    
                                                    elif x == 'b':
                                                        break
                                                      
                                                    else:
                                                        print('WARNING: {} is an unknown option. Try again'.format(x))
                                                    continue
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed. Shutting Down')
                                                close()
                                            
                                        elif x == '21':
                                            try:
                                                while True:
                                                    options = """\n    Netflix DRM \n                            
                                 1 - Check Netflix DRM 
                                 2 - Remove Netflix DRM
                                 q - quit
                                 b - back
                                 """
                                                    print(options)
                                                    x = input('>: ')
                                                    
                                                    if x== '1':
                                                        sshSettingsCommand('ls -l /mnt/ffs/permanent/infield_drm/')
                                                        continue
                                                        
                                                    if x == '2':
                                                        sshCmd('rm -rf /mnt/ffs/permanent/infield_drm/')
                                                        continue
                                                                     
                                                    if x == 'q':
                                                        close()
                                                        sys.exit(0)
                                             
                                                    elif x == 'b':
                                                        break
                                                      
                                                    else:
                                                        print('WARNING: {} is an unknown option. Try again'.format(x))
                                                    continue
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed. Shutting Down')
                                                close()
                                                                            
                                        elif x == 'r':
                                            stbReboot()
                                        
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                                    
                            elif x == '22': # Reporting settings
                                try:
                                    while True:
                                        if stbPrimary.get('updateDelay') is None:
                                            print ('No reporting settings')
                                        
                                        else:
                                            print('\nReporting settings\n '
                                            'Update Delay: ' + stbPrimary["updateDelay"] + '   App Config: ' + stbPrimary["appConfigReportDelay"] + '   Reporting enabled:' + stbPrimary["reportingEnabled"]
                                            + '\n Reporting URL: ' + stbPrimary["reportinguri"]
                                            + '\n Send to local file: ' + stbPrimary["sendEventsToLocalFileOnly"]+ '   Bundle size: ' + stbPrimary["ams.numEventsInBundle"]+ '   Cache size: ' + stbPrimary["ams.CacheSize"]
                                            + '\n AMS ID: ' + stbPrimary["AmsID"])
                                            
                                        options = """\n     Reporting
                             0 - Read settings from STB
                             1 - Set update Delay
                             2 - Set application Config Report Delay
                             3 - Enable Reporting
                             4 - Set URL
                             5 - Send Events to Local File Only
                             6 - Set Event Bundle Size
                             7 - Set Event Cache size
                             8 - Set AmsID
                             9 - Configure STB for Reporting (TBC)\n
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x == '0':
                                            readSettings('settings_cli Get "tungsten.ams.enabled"')
                                            ss1 = saveSetting.replace('"tungsten.ams.enabled" , "', '')
                                            stbPrimary.update({"reportingEnabled": ss1})  # add STB ams/reporting enabled to stbPrimary dictionary
                                            readSettings('settings_cli Get "tungsten.ams.updateDelay" ')
                                            ss1 = saveSetting.replace('"tungsten.ams.updateDelay" , "', '')
                                            stbPrimary.update({"updateDelay": ss1})  # add Reporting message delay to stbPrimary dictionary
                                            readSettings('settings_cli Get "tungsten.reporting_service.appConfigReportDelay" ')
                                            ss1 = saveSetting.replace('"tungsten.reporting_service.appConfigReportDelay" , "', '')
                                            stbPrimary.update({"appConfigReportDelay": ss1})  # add Reporting Config delay to stbPrimary dictionary
                                            readSettings('settings_cli get tungsten.reporting_service.uri')
                                            ss1 = saveSetting.replace('"tungsten.reporting_service.uri" , "', '')
                                            stbPrimary.update({"reportinguri": ss1})  # add reporting uri to stbPrimary dictionary
                                            readSettings('settings_cli Get "tungsten.reporting_service.sendEventsToLocalFileOnly" ')
                                            ss1 = saveSetting.replace('"tungsten.reporting_service.sendEventsToLocalFileOnly" , "', '')
                                            stbPrimary.update({"sendEventsToLocalFileOnly": ss1})  # EventsToLocalFileOnly to stbPrimary dictionary
                                            readSettings('settings_cli Get "tungsten.ams.numEventsInBundle" ')
                                            ss1 = saveSetting.replace('"tungsten.ams.numEventsInBundle" , "', '')
                                            stbPrimary.update({"ams.numEventsInBundle": ss1})  # add reportingEventsInBundle to stbPrimary dictionary
                                            readSettings('settings_cli Get "tungsten.ams.cacheSize" ')
                                            ss1 = saveSetting.replace('"tungsten.ams.cacheSize" , "', '')
                                            stbPrimary.update({"ams.CacheSize": ss1})  # add reportingCacheSize to stbPrimary dictionary
                                            readSettings('settings_cli Get "tungsten.ams.AmsID"')
                                            ss1 = saveSetting.replace('"tungsten.ams.AmsID" , "', '')
                                            stbPrimary.update({"AmsID": ss1})  # add AmsID to stbPrimary dictionary
                                   
                                        elif x == '1': # Reporting Delay
                                            reporting_time = 0
                                            reportingDelay(reporting_time)
                                            sshSettingsCommand(reportDelay)
                                            readSettings('settings_cli Get "tungsten.ams.updateDelay" ')
                                            ss1 = saveSetting.replace('"tungsten.ams.updateDelay" , "', '')
                                            stbPrimary.update({"updateDelay": ss1})  # add Reporting message delay to stbPrimary dictionary
                                            continue

                                        elif x == '2': # App Config Delay
                                            config = 0
                                            appConfigReportDelay(config)
                                            sshSettingsCommand(appConfigDelay)
                                            readSettings('settings_cli Get "tungsten.reporting_service.appConfigReportDelay" ')
                                            ss1 = saveSetting.replace('"tungsten.reporting_service.appConfigReportDelay" , "', '')
                                            stbPrimary.update({"appConfigReportDelay": ss1})  # add Reporting Config delay to stbPrimary dictionary
                                            continue

                                        elif x == '3': # # Enable/Disable reporting
                                            enable = input('Enter "True" to enable, or "False" to disable reporting: ')
                                            reporting_enable(enable)
                                            sshSettingsCommand(enableCommand)
                                            readSettings('settings_cli Get "tungsten.ams.enabled"')
                                            ss1 = saveSetting.replace('"tungsten.ams.enabled" , "', '')
                                            stbPrimary.update({"reportingEnabled": ss1})  # add STB ams/reporting enabled to stbPrimary dictionary
                                            continue

                                        elif x == '4': # Change reporing URL (Reporting server that the STB sends to)
                                            url = 0
                                            #reportingUrl = (input('Enter required URL, leave blank to set default: "https://8uc2224o95.execute-api.eu-west-2.amazonaws.com/default/reportingIon": ')
                                                #or "https://8uc2224o95.execute-api.eu-west-2.amazonaws.com/default/reportingIon")
                                            server_URL(url)
                                            sshSettingsCommand(server)
                                            readSettings('settings_cli get tungsten.reporting_service.uri')
                                            ss1 = saveSetting.replace('"tungsten.reporting_service.uri" , "', '')
                                            stbPrimary.update({"reportinguri": ss1})  # add reporting uri to stbPrimary dictionary
                                            continue

                                        elif x == '5': #  Enable Disable send reporting to file
                                            disable = input('Enter "True" to enable, or "False" to disable, Send Events to Local File Only: ')
                                            print(disable)
                                            fileStr = str(disable)
                                            command = 'settings_cli Set "tungsten.reporting_service.sendEventsToLocalFileOnly" '
                                            fileCommand = command + fileStr
                                            print(fileCommand)                                
                                            sshSettingsCommand(fileCommand)
                                            readSettings('settings_cli Get "tungsten.reporting_service.sendEventsToLocalFileOnly" ')
                                            ss1 = saveSetting.replace('"tungsten.reporting_service.sendEventsToLocalFileOnly" , "', '')
                                            stbPrimary.update({"sendEventsToLocalFileOnly": ss1})  # EventsToLocalFileOnly to stbPrimary dictionary
                                            continue

                                        elif x == '6': # Change amount of events in a bundle
                                            bundle = input('Enter Required number of events required in Bundle(default = 500): ')
                                            bundleStr = str(bundle)
                                            command = 'settings_cli Set "tungsten.ams.numEventsInBundle" '
                                            eventBundle = command + bundleStr
                                            print(eventBundle)
                                            sshSettingsCommand(eventBundle)
                                            readSettings('settings_cli Get "tungsten.ams.numEventsInBundle" ')
                                            ss1 = saveSetting.replace('"tungsten.ams.numEventsInBundle" , "', '')
                                            stbPrimary.update({"ams.numEventsInBundle": ss1})  # add reportingEventsInBundle to stbPrimary dictionary                                
                                            continue

                                        elif x == '7': # Change Cached memory size
                                            cache = input('Enter Required Cache size (default = 1000): ')
                                            cacheStr = str(cache)
                                            command = 'settings_cli Set "tungsten.ams.cacheSize" '
                                            cacheSize = command + cacheStr
                                            print(cacheSize)
                                            sshSettingsCommand(cacheSize)
                                            readSettings('settings_cli Get "tungsten.ams.cacheSize" ')
                                            ss1 = saveSetting.replace('"tungsten.ams.cacheSize" , "', '')
                                            stbPrimary.update({"ams.CacheSize": ss1})  # add reportingCacheSize to stbPrimary dictionary
                                            continue

                                        elif x == '8': #Get AMS ID (used to be used to find STB on reporting server
                                            ams = 0
                                            AmsID(ams)
                                            print(AmsID)
                                            sshSettingsCommand(AmsID)
                                            readSettings('settings_cli Get "tungsten.ams.AmsID"')
                                            ss1 = saveSetting.replace('"tungsten.ams.AmsID" , "', '')
                                            stbPrimary.update({"AmsID": ss1})  # add AmsID to stbPrimary dictionary
                                            continue
                                            
                                        elif x == '9':
                                            reportingSetup()
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                            
                                        elif x == 'b':
                                            break
                                        
                                        elif x == 'r':
                                            stbReboot()
                                        
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed.')
                                    #close()
                                                                  
                            elif x == '23':
                                try:
                                    while True:
                                        if stbPrimary.get('watermark.profile') is None:
                                            print ('No reporting settings')
                                        
                                        else:
                                            print('\nWatermark settings\n '
                                            'Watermark Profile: ' + stbPrimary["watermark.profile"] + '   Watermark Alpha: ' + stbPrimary["watermark.alpha"] + '   Watermark enabled:' + stbPrimary["watermark.enabled"])
                
                                        options = """    watermark
                                        
                             0 - read Watermark settings
                             1 - Watermark profile
                             2 - Watermark alpha
                             3 - Watermark Enable \n
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get tungsten.watermark.profile')
                                            ss1 = saveSetting.replace('"tungsten.watermark.profile" , "', '')
                                            stbPrimary.update({"watermark.profile": ss1})  # add STB waterwmark profile to stbPrimary dictionary
                                            readSettings('settings_cli get tungsten.watermark.alpha')
                                            ss1 = saveSetting.replace('"tungsten.watermark.alpha" , "', '')
                                            stbPrimary.update({"watermark.alpha": ss1})  # add STB watermark alpha to stbPrimary dictionary
                                            readSettings('settings_cli get tungsten.watermark.enabled')
                                            ss1 = saveSetting.replace('"tungsten.watermark.enabled" , "', '')
                                            stbPrimary.update({"watermark.enabled": ss1})  # add STB auto Standby Time to stbPrimary dictionary
                                           
                                        elif x == '1':
                                            enter = input('Enter require Watermark Profile(2,255): ')
                                            profile = str(enter)
                                            command = 'settings_cli Set "tungsten.watermark.profile" '
                                            global updateProfile
                                            updateProfile = command + profile
                                            print(updateProfile)
                                            sshSettingsCommand(updateProfile)
                                            readSettings('settings_cli get tungsten.watermark.profile')
                                            ss1 = saveSetting.replace('"tungsten.watermark.profile" , "', '')
                                            stbPrimary.update({"watermark.profile": ss1})  # add STB waterwmark profile to stbPrimary dictionary
                                            
                                        elif x == '2':
                                            enter = input('Enter require Watermark Alpha(1-100): ')
                                            alpha = str(enter)
                                            command = 'settings_cli Set "tungsten.watermark.alpha" '
                                            global updateAlpha
                                            updateAlpha = command + alpha
                                            print(updateAlpha)
                                            sshSettingsCommand(updateAlpha)
                                            readSettings('settings_cli get tungsten.watermark.alpha')
                                            ss1 = saveSetting.replace('"tungsten.watermark.alpha" , "', '')
                                            stbPrimary.update({"watermark.alpha": ss1})  # add STB watermark alpha to stbPrimary dictionary
                                            
                                        elif x == '3':
                                            enter = input('Enter "True" to enable, or "False" to disable Watermark: ')
                                            watermark = str(enter)
                                            command = 'settings_cli Set "tungsten.watermark.enabled" '
                                            global updateWatermark
                                            updateWatermark = command + watermark
                                            sshSettingsCommand(updateWatermark)
                                            readSettings('settings_cli get tungsten.watermark.enabled')
                                            ss1 = saveSetting.replace('"tungsten.watermark.enabled" , "', '')
                                            stbPrimary.update({"watermark.enabled": ss1})  # add STB auto Standby Time to stbPrimary dictionary
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                        
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()    

                            
                            elif x == '24':
                                try:
                                    while True:
                                        options = """               Low memory value settings \n                            
                             0 - Read all Low Momory Values \n
                                ***NETFLIX*** \n
                             10 - Read Netflix Low Memory settings
                             11 - Netflix free memory low mark
                             12 - Netflix free memory req for foreground
                             13 - Netflix free process memory mark
                             14 - Read Netflix free memory req for suspend \n
                             ***Amazon PV*** \n
                             20 - Amazon Low Memory Settings
                             21 - Amazon free memory low mark
                             22 - Amazon free memory req for foreground
                             23 - Amazon free process memory mark
                             24 - Amazon free memory req for suspend \n
                                ***WPE*** \n
                             30 - WPE Low Memory Settings
                             31 - WPE free memory low mark
                             32 - WPE free memory req for foreground
                             33 - WPE free process memory mark
                             34 - WPE free memory req for suspend \n
                                ***Youtube*** \n
                             40 - Youtube Low Memory Settings
                             41 - Youtube free memory low mark 
                             42 - Netflix free memory req for foreground \n             
                                
                             q - quit
                             b - Back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get tungsten.appmanager.netflix_free_memory_low_mark')
                                            readSettings('settings_cli get appmanager.netflix_free_memory_req_for_foreground')
                                            readSettings('settings_cli get appmanager.netflix_process_memory_mark')
                                            readSettings('settings_cli get appmanager.netflix_free_memory_req_for_suspend')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_free_memory_low_mark')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_free_memory_req_for_foreground')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_process_memory_mark')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_free_memory_req_for_suspend')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_free_memory_low_mark')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_free_memory_req_for_foreground')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_free_memory_req_for_suspend')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_process_memory_mark')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_free_memory_low_mark')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_free_memory_req_for_foreground')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_free_memory_req_for_suspend')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_process_memory_mark')
                                            
                                        elif x == '10': # Netflix
                                            readSettings('settings_cli get tungsten.appmanager.netflix_free_memory_low_mark')
                                            readSettings('settings_cli get appmanager.netflix_free_memory_req_for_foreground')
                                            readSettings('settings_cli get appmanager.netflix_process_memory_mark')
                                            readSettings('settings_cli get appmanager.netflix_free_memory_req_for_suspend')
                                            
                                        elif x == '11': # Netflix
                                            enter = input('Enter required value for Netflix free memory low mark: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.netflix_free_memory_low_mark" '
                                            netflixLowMark = command + lowMark
                                            sshSettingsCommand(netflixLowMark)
                                            
                                        elif x == '12': # Netflix
                                            enter = input('Enter required value for Netflix free memory req for foreground: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.netflix_free_memory_req_for_foreground" '
                                            netflixForeground = command + lowMark
                                            sshSettingsCommand(netflixForeground)
                                            
                                        elif x == '13': # Netflix
                                            enter = input('Enter required value for Netflix free process memory mark: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.netflix_process_memory_mark" '
                                            netflixProcess = command + lowMark
                                            sshSettingsCommand(netflixProcess)
                                            
                                        elif x == '14': # Netflix
                                            enter = input('Enter required value for Netflix free memory req for suspend: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.netflix_free_memory_req_for_suspend" '
                                            netflixSuspend = command + lowMark
                                            sshSettingsCommand(netflixSuspend)
                                            
                                        elif x == '20': # Amazon Browser
                                            readSettings('settings_cli get tungsten.appmanager.amazon_free_memory_low_mark')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_free_memory_req_for_foreground')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_free_memory_req_for_suspend')
                                            readSettings('settings_cli get tungsten.appmanager.amazon_process_memory_mark')
                                            
                                        elif x == '21': # Amazon Browser
                                            enter = input('Enter required value for Amazon free memory low mark: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.amazon_free_memory_low_mark" '
                                            amazonLowMark = command + lowMark
                                            sshSettingsCommand(amazonLowMark)
                                            
                                        elif x == '22': # Amazon Browser
                                            enter = input('Enter required value for Amazon free memory req for foreground: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.amazon_free_memory_req_for_foreground" '
                                            amazonForeground = command + lowMark
                                            sshSettingsCommand(amazonForeground)
                                            
                                        elif x == '23': # Amazon Browser
                                            enter = input('Enter required value for Amazon free process memory mark: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.amazon_process_memory_mark" '
                                            amazonProcess = command + lowMark
                                            sshSettingsCommand(amazonProcess)
                                            
                                        elif x == '24': # Amazon Browser
                                            enter = input('Enter required value for Amazon free memory req for suspend: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.amazon_free_memory_req_for_suspend" '
                                            amazonSuspend = command + lowMark
                                            sshSettingsCommand(amazonSuspend)
                                            
                                        elif x == '30': # WPE Browser
                                            readSettings('settings_cli get tungsten.appmanager.wpe_free_memory_low_mark')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_free_memory_req_for_foreground')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_process_memory_mark')
                                            readSettings('settings_cli get tungsten.appmanager.wpe_free_memory_req_for_suspend')
                                            
                                        elif x == '31': # WPE Browser
                                            enter = input('Enter required value for WPE Browser free memory low mark: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.wpe_free_memory_low_mark" '
                                            wpeLowMark = command + lowMark
                                            sshSettingsCommand(wpeLowMark)
                                            
                                        elif x == '32': # WPE Browser
                                            enter = input('Enter required value for WPE Browser free memory req for foreground: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.wpe_free_memory_req_for_foreground" '
                                            wpeForeground = command + lowMark
                                            sshSettingsCommand(wpeForeground)
                                            
                                        elif x == '33': # WPE Browser
                                            enter = input('Enter required value for WPE Browser free process memory mark: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.wpe_process_memory_mark" '
                                            wpeProcess = command + lowMark
                                            sshSettingsCommand(wpeProcess)
                                            
                                        elif x == '34': # WPE Browser
                                            enter = input('Enter required value for WPE Browser free memory req for suspend: ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.wpe_free_memory_req_for_suspend" '
                                            wpeSuspend = command + lowMark
                                            sshSettingsCommand(wpeSuspend)
                                            
                                        elif x == '40': # Youtube
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_free_memory_low_mark')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_free_memory_req_for_foreground')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_free_memory_req_for_suspend')
                                            readSettings('settings_cli get tungsten.appmanager.cobalt_process_memory_mark')
                                            
                                        elif x == '41': # Youtube
                                            enter = input('Enter required value for Youtube free memory low mark (default = 153600): ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.cobalt_free_memory_low_mark" '
                                            youtubeLowMark = command + lowMark
                                            sshSettingsCommand(youtubeLowMark)
                                            
                                        elif x == '42': # Youtube
                                            enter = input('Enter required value for Youtube free memory req for foreground (default value = 225280): ')
                                            lowMark = str(enter)
                                            command = 'settings_cli set "tungsten.appmanager.cobalt_free_memory_req_for_foreground" '
                                            youtubeForeground = command + lowMark
                                            sshSettingsCommand(youtubeForeground)
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)    
                                            
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                            
                            elif x == '25':
                                try:
                                    while True:
                                        options = """\n    Time Management settings \n                            
                             0 - read time mangement priorities
                             1 - Reset time management priorities to default
                             2 - Set all time management priorities to 0 
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get tungsten.timemanagement.CablePriority')
                                            readSettings('settings_cli get tungsten.timemanagement.SatellitePriority')
                                            readSettings('settings_cli get tungsten.timemanagement.HTTPSPriority')
                                            readSettings('settings_cli get tungsten.timemanagement.TerrestrialPriority')
                                            readSettings('settings_cli get tungsten.timemanagement.IPPriority')
                                            
                                        elif x == '1':
                                            confirm = input('You are about to reset all time management priorities to default this will also reboot the STB do you want to continue Y : ')
                                
                                            if confirm == 'Y':
                                                sshCmd('settings_cli set tungsten.timemanagement.CablePriority 1')
                                                sshCmd('settings_cli set tungsten.timemanagement.SatellitePriority 2')
                                                sshCmd('settings_cli set tungsten.timemanagement.HTTPSPriority 3')
                                                sshCmd('settings_cli set tungsten.timemanagement.TerrestrialPriority 4')
                                                sshCmd('settings_cli set tungsten.timemanagement.IPPriority 0')
                                                stbReboot()
                                                
                                        elif x == '2':
                                            confirm = input('You are about to set all time management priorities to 0 this will also reboot the STB do you want to continue Y : ')
                                
                                            if confirm == 'Y':
                                                sshCmd('settings_cli set tungsten.timemanagement.CablePriority 0')
                                                sshCmd('settings_cli set tungsten.timemanagement.SatellitePriority 0')
                                                sshCmd('settings_cli set tungsten.timemanagement.HTTPSPriority 0')
                                                sshCmd('settings_cli set tungsten.timemanagement.TerrestrialPriority 0')
                                                sshCmd('settings_cli set tungsten.timemanagement.IPPriority 0')
                                                stbReboot()
                                                
                                        elif x == '3':
                                            print('enable')
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close() 
                            
                            elif x == '26':
                                try:
                                    while True:
                                        options = """\n    
                    Sceensaver Settings \n                            
                 0 - read Screen saver settings
                 1 - Set Screensaver enabled setting
                 2 - Set Screensaver timeout
                 3 - Set API Path
                 4 - Delete Screen saver setting
                 5 - Delete Screensaver Timeout
                 6 - Delete API Path
                 q - quit
                 b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_SCREENSAVER_ENABLED"')
                                            if 'Error:key' in saveSetting:
                                                print ("No setting on STB") 
                                            else:
                                                print ("Saving setting")
                                                ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_SCREENSAVER_ENABLED" , "', '')
                                                stbPrimary.update({"screenSaverEnabled":ss1})

                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_TIMEOUT_LENGTH"')
                                            if 'Error:key' in saveSetting:
                                                print ("No setting on STB") 
                                            else:
                                                print ("Saving setting")
                                                ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_TIMEOUT_LENGTH" , "', '')
                                                stbPrimary.update({"screenSaverTimeout": ss1})

                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH"')
                                            if 'Error:key' in saveSetting:
                                                print ("No setting on STB") 
                                            else:
                                                print ("Saving setting")
                                                ss1 = saveSetting.replace(' "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH" , "', '')
                                                stbPrimary.update({"screenSaverPath": ss1})
                                                                     
                                        elif x == '1':
                                            enter = input('Enter "true" to enable, or "false" to disable Screen saver: ')                                           
                                            enable = str(enter)
                                            command = 'settings_cli Set "application.mainapp.UI_SETTING_SCREENSAVER_ENABLED" '
                                            ssEnable = command + enable
                                            sshSettingsCommand(ssEnable)
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_SCREENSAVER_ENABLED"')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_SCREENSAVER_ENABLED" , "', '')
                                            stbPrimary.update({"screenSaverEnabled":ss1})
                                            locationReload()

                                        elif x == '2':
                                            enter = input('Enter Timeout value, in milliseconds for Screensaver (10000 = 10 seconds, 60000 = 1 min: ')
                                            timeout = str(enter)
                                            command = 'settings_cli Set "application.mainapp.UI_SETTING_TIMEOUT_LENGTH" '
                                            ssEnable = command + timeout
                                            sshSettingsCommand(ssEnable)
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_TIMEOUT_LENGTH"')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_TIMEOUT_LENGTH" , "', '')
                                            stbPrimary.update({"screenSaverTimeout": ss1})
                                            locationReload()

                                        elif x == '3':
                                            enter = input('Enter Screensaver API Path, the example paths below are from test cases \n'
'- "carousels/Movies/Featured/NewMovies"\n'
'- "carousels/TVShows/Comedy/LiveNews"\n'
'- "taps/genericQueryTap?fq=releaseYear:2025 and objectType:Movie and descriptors.moods:[* TO *]&fl=*,images&limit=15&group=true&group.by=altIds.groupId&"\n>: ')
                                            path = str(enter)
                                            command = 'settings_cli Set "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH" '
                                            ssPath = command + path
                                            sshSettingsCommand(ssPath)
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH"')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_SCREENSAVER_API_PATH" , "', '')
                                            stbPrimary.update({"screenSaverPath": ss1})
                                            locationReload()
                                                                                        
                                        elif x == '4':
                                            sshSettingsCommand('settings_cli del "application.mainapp.UI_SETTING_SCREENSAVER_ENABLED"')
                                            stbPrimary.pop("screenSaverEnabled")
                                            locationReload()
                            
                                        elif x == '5':
                                            sshSettingsCommand('settings_cli del "application.mainapp.UI_SETTING_TIMEOUT_LENGTH"')
                                            stbPrimary.pop("screenSaverTimeout")
                                            locationReload()

                                        elif x == '6':
                                            sshSettingsCommand('settings_cli del "application.mainapp.UI_SETTING_SCREENSAVER_API_PATH"')
                                            stbPrimary.pop("screenSaverPath")
                                            locationReload()
                        
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                            
                            elif x == '27': # 
                                try:
                                    while True:
                                        options = """\n      Testers Default/Reset Settings      \n  
                  0 - Get User Settings from file
                  1 - Set Default file with setting from current STB
                  2 - Update User settings Default Settings
                  3 - List of settings included in default 
                  4 - Reset settings to last saved version - TBC
                  r - reboot\n                  q - quit\n                  b - back\n        """

                                        print(options)
                                        x = input('>: ')

                                        if x == '0':
                                            readDefaultFile()
                                            #print (stbPrimary)
                                            for x, y in stbPrimary.items():
                                                print(x,':', y)
                                            
                                        elif x == '1': #keeping to use as update default settings
                                            writeDefaultFile()

                                        elif x == '2':
                                            readDefaultFile()
                                            updateUserSettings()
                                            settingsRead()

                                        elif x == '3':
                                            print(""" *** Default Tester Settings ***
             tungsten.ams.updateDelay"\n tungsten.ams.enabled\n tungsten.reporting_service.uri\n tungsten.ux.autoStandbyTimeout
 tungsten.watermark.profile\n tungsten.watermark.alpha\n tungsten.watermark.enabled\n tungsten.ux.ParentalPincode""")

                                        elif x == '4':
                                            print ('4 selected')
                                            confirm = input('This will restore STB default settings to the last known values, ideally after a FSR or when the STB is of unknown state. \nValues are saved Manually, Save settings on main options list, or on exit of this script? To continue enter Y: ')
                                
                                            if confirm == 'Y':
                                                print ('Y selected')
                                                #readmySTBsFile()
                                                #getSTBdetails()
                                                #updateUserSettings()
                                                #settingsRead()
                                                                                  
                                            else:
                                                print('canceled')                                

                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        elif x == 'r':
                                            stbReboot()

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()

                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()

                elif x == '30':
                    try:
                        while True:
                            options = """
                    *** Developer Settings ***
                  31 - Download in IP mode
                  32 - Disable "reset iQ system" 
                  33 - Customer Education screen
                  34 - Connect to alternative PTS Server
                  35 - Point STB at different provisioning services
                  b - back
                  q - quit\n 
                  """
                            print(options)
                            x = input('>: ')

                            if x == '31': # Download in IP mode
                                try:
                                    while True:
                                        options = """\n      Set Allow Download in IP Mode      \n                            
                             0 - Check current setting
                             1 - Allow Download in IP mode 
                             2 - Turn off Download in IP Mode
                             3 - When renting from store Download/Stream
                             4 - When watching Foxtel On Demand content Download/Stream
                             q - quit
                             b - back                 """
                                        print(options)
                                        x = input('>: ')

                                        if x== '0':
                                            print('Checking Allow Download in IP Mode settings an user download setting values')
                                            sshSettingsCommand('settings_cli Get "application.mainapp.ALLOW_DOWNLOAD_IN_IP_MODE"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_PPV_PLAYBACK_TYPE"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_ON_DEMAND_PLAYBACK_TYPE"')
                                                                                                       
                                        elif x== '1': #Allow IP download
                                            sshSettingsCommand('settings_cli Set "application.mainapp.ALLOW_DOWNLOAD_IN_IP_MODE" "true"')
                                            print('Setting Allow Download in IP Mode to True')
                                                                           
                                        elif x == '2': #Don't allow IP Download
                                            sshSettingsCommand('settings_cli Set "application.mainapp.ALLOW_DOWNLOAD_IN_IP_MODE" "false"')
                                            print('Setting Allow Download in IP Mode to False')
                                                                            
                                        elif x == '3':  #TVOD playback type
                                            pbTypeChoosen = str(input('Enter required mode: stream or download: '))
                                            if pbTypeChoosen in playbackType:
                                                print(pbTypeChoosen + ' Selected')
                                                sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_PPV_PLAYBACK_TYPE','%s')"  """"" % pbTypeChoosen)
                                                
                                            else:
                                                print('Audio format not recognised. Try again')
                                            
                                        elif x == '4':  #SVOD playback type                          
                                            pbTypeChoosen = str(input('Enter required mode: stream or download: '))
                                            if pbTypeChoosen in playbackType:
                                                print(pbTypeChoosen + ' Selected')
                                                sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_ON_DEMAND_PLAYBACK_TYPE','%s')"  """"" % pbTypeChoosen)
                                                
                                            else:
                                                print('Audio format not recognised. Try again')                      
                                        
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                            
                            elif x == '32': # Disable Reset iQ system 
                                try:
                                    while True:
                                        options = """\n      Set Allow Download in IP Mode      \n                            
                             0 - Check current setting - 
                             1 - Enable "reset iQ System" - "application.mainapp.SYSTEM_RESET_DISABLED" "true"
                             2 - Disable "reset iQ system" - "application.mainapp.SYSTEM_RESET_DISABLED" "false"
                             3 - Delete "reset iQ system" setting
                             q - quit
                             b - back                 """
                                        print(options)
                                        x = input('>: ')

                                        if x== '0':
                                            print('Checking reset iQ system setting')
                                            sshSettingsCommand('settings_cli Get "application.mainapp.SYSTEM_RESET_DISABLED"')
                                            #readSettings('settings_cli get "application.mainapp.UI_SETTING_PPV_PLAYBACK_TYPE"')
                                             
                                        elif x== '1': #Disable
                                            sshSettingsCommand('settings_cli set "application.mainapp.SYSTEM_RESET_DISABLED" "true"')
                                            print('Disable "reset iQ System"')
                                            stbReboot()
                                                                           
                                        elif x == '2': #Enable
                                            sshSettingsCommand('settings_cli set "application.mainapp.SYSTEM_RESET_DISABLED" "false"')
                                            print('Enable "reset iQ System"')
                                            stbReboot()
                                            
                                        elif x == '3': #Delete
                                            sshSettingsCommand('settings_cli del "application.mainapp.SYSTEM_RESET_DISABLED"')
                                            print('Deleting "reset iQ System" setting')
                                                        
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                            
                            elif x == '33': # Customer education screen

                                try:
                                    while True:
                                        options = """\n      Education Screen Settings e      \n                            
                             0 - Check current setting - 
                             1 - Clear the flag  
                             q - quit
                             b - back
                             r - reboot                 """
                                        print(options)
                                        x = input('>: ')

                                        if x== '0':
                                            print('Checking Education screen Software versions')
                                            sshSettingsCommand('settings_cli Get "application.mainapp.UI_SETTING_EDUCATION_PAST_SOFTWARE_VERSIONS"')
                                            
                                        elif x== '1': #Delete
                                            sshSettingsCommand('settings_cli del "application.mainapp.UI_SETTING_EDUCATION_PAST_SOFTWARE_VERSIONS" ')
                                            print('The Education past software versions have been cleared')
                                            #stbReboot()
                                                                           
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        elif x == 'r':
                                            stbReboot()
                                        
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                            
                            elif x == '34': # Connect to PTS
                                try:
                                    while True:
                                        options = """\n   
                  Connect to PTS Enviroment     \n                            
                 1 - Connect to settings_cli Set "application.mainapp.epg.sdp_host" "services.t1.foxtel-iq.com.au" 
                 2 - Disconnect from PTS settings_cli Set "application.mainapp.epg.sdp_host" "services.p1.foxtel-iq.com.au"
                 q - quit
                 b - back                 """
                                        print(options)
                                        x = input('>: ')

                                        if x == '1':
                                            sshSettingsCommand('settings_cli Set "application.mainapp.epg.sdp_host" "services.t1.foxtel-iq.com.au"')
                                            print('Connecting to PTS')
                                            stbReboot()
                                            
                                        elif x == '2':
                                            sshSettingsCommand('settings_cli Set "application.mainapp.epg.sdp_host" "services.p1.foxtel-iq.com.au"')
                                            print('Disconnecting from PTS')
                                            stbReboot()
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)

                                        elif x == 'b':
                                            break

                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue

                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()

                            elif x == '35':
                                try:
                                    while True:
                                        options = """\n    Point STB at different provisioning services \n                            
                         0 - read
                         1 - Set provisioning.play_service to server http://tu-services.arrisi.com:5001
                         2 - Set default provisioning.play_service 
                         3 - Set provisioning.cdn_url_service to server http://tu-services.arrisi.com:5001
                         4 - Set default provisioning.cdn_url_service
                         5 - Set own  provisioning.play_service
                         6 - Set own  provisioning.cdn_url_service
                         q - quit
                         b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli Get "tungsten.provisioning.play_service"')
                                            readSettings('settings_cli get "tungsten.provisioning.cdn_url_service"')
                                                                           
                                        elif x == '1':
                                            sshSettingsCommand('settings_cli Set "tungsten.provisioning.play_service" "http://tu-services.arrisi.com:5001/queryPlayService"')
                                             
                                        elif x == '2':
                                            sshSettingsCommand('settings_cli Set "tungsten.provisioning.play_service" "https://services.p1.foxtel-iq.com.au/fxtl/v1/play"')
                                            
                                        elif x == '3':
                                            sshSettingsCommand('settings_cli Set "tungsten.provisioning.cdn_url_service" "http://tu-services.arrisi.com:5001/queryPlayService"')
                                            
                                        elif x == '4':
                                            sshSettingsCommand('settings_cli Set "tungsten.provisioning.cdn_url_service" "https://services.p1.foxtel-iq.com.au/fxtl/v1/cdnUrl"')
                                            
                                        elif x == '5':
                                            enter = input('Enter youe URL of provisioning play Service eg "https://fake-services.catalogue.foxtel.com.au/fxtl/v1/play" : ')
                                            playService = str(enter)
                                            command = 'settings_cli Set "tungsten.provisioning.play_service" '
                                            updatePlayService = command + playService
                                            #print (updatePlayService)
                                            sshSettingsCommand(updatePlayService)
                                            
                                        elif x == '6':
                                            enter = input('Enter youe URL of provisioning cdn_url service eg "https://fake-services.catalogue.foxtel.com.au/fxtl/v1/play" : ')
                                            cdn_url = str(enter)
                                            command = 'settings_cli Set "tungsten.provisioning.cdn_url_service" '
                                            update_cdn_url = command + cdn_url
                                            #print (update_cdn_url)
                                            sshSettingsCommand(update_cdn_url)
                                        
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()


                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()

                elif x == '40':
                    try:
                        while True:
                            options = """
                    *** User Settings ***
                  41 - Audio Settings 
                  42 - Parental control Settings
                  43 - Streaming and download settings
                  44 - Remote Control Settings \n
                  b - back
                  q - quit\n 
                  """
                            print(options)
                            x = input('>: ')

                            if x == '41':
                                try:
                                    while True:
                                        options = """    Audio settings \n                            
                             0 - read Audio Settings 
                             1 - SPDIF Format
                             2 - HDMI Format
                             3 - SPDIF Attenuation
                             4 - HDMI Attenuation
                             5 - SPDIF Delay
                             6 - HDMI Delay
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get "tungsten.ux.audioSettingsFormatSpdif"')
                                            ss1 = saveSetting.replace('"tungsten.ux.audioSettingsFormatSpdif" , "', '')
                                            stbPrimary.update({"audioSettingsFormatSpdif": ss1}) #add SPDIF value to stbPrimary
                                            readSettings('settings_cli get "tungsten.ux.audioSettingsFormatHdmi"')
                                            ss1 = saveSetting.replace('"tungsten.ux.audioSettingsFormatHdmi" , "', '')
                                            stbPrimary.update({"audioSettingsFormatHdmi": ss1}) #add HDMI value to stbPrimary
                                            readSettings('settings_cli get "tungsten.ux.digitalAudioLevel"')
                                            ss1 = saveSetting.replace('"tungsten.ux.digitalAudioLevel" , "', '')
                                            stbPrimary.update({"digitalAudioLevel": ss1}) #add SPDIF Attenuation value to stbPrimary
                                            readSettings('settings_cli get "tungsten.ux.digitalAudioLevelHdmi"')
                                            ss1 = saveSetting.replace('"tungsten.ux.digitalAudioLevelHdmi" , "', '')
                                            stbPrimary.update({"digitalAudioLevelHdmi": ss1})#add HDMI Attenuation value to stbPrimary
                                            readSettings('settings_cli get "tungsten.ux.audioDelay"')
                                            ss1 = saveSetting.replace('"tungsten.ux.audioDelay" , "', '')
                                            stbPrimary.update({"audioDelay": ss1})#add SPDIF sudio Delay value to stbPrimary
                                            readSettings('settings_cli get "tungsten.ux.audioDelayHdmi"')
                                            ss1 = saveSetting.replace('"tungsten.ux.audioDelayHdmi" , "', '')
                                            stbPrimary.update({"audioDelayHdmi": ss1})#add HDMI Audio Delay Delay value to stbPrimary
                                              
                                        elif x == '1': #SPDIF Format
                                            try:
                                                while True:    
                                                    a_format = str(input('Enter Spdif Audio format, Dolby or Stereo: '))
                                                    if a_format in audio:
                                                        print(a_format + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.audioSettingsFormatSpdif" '
                                                        spdifFormat = command + a_format
                                                        sshSettingsCommand(spdifFormat)
                                                        break
                                                         
                                                    print('Audio format not recognised. Try again')
                                                    continue
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')          
                                            
                                        elif x == '2': #HDMI Format
                                            try:
                                                while True:    
                                                    a_format = str(input('Enter HDMI Audio format, Dolby or Stereo: '))
                                                    if a_format in audio:
                                                        print(a_format + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.audioSettingsFormatHdmi" '
                                                        hdmiFormat = command + a_format
                                                        sshSettingsCommand(hdmiFormat)
                                                        break
                                                        
                                                    print('Audio format not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')
                                                
                                        elif x == '3': # SPDIF Attenuation
                                            try:
                                                while True:    
                                                    attenuation = str(input('Enter SPDIF Audio Attenuation, Enter 0dB -3dB -6dB -9dB -11dB: '))
                                                    if attenuation in audioAtt:
                                                        print(attenuation + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.digitalAudioLevel" '
                                                        spdifAtt = command + attenuation
                                                        sshSettingsCommand(spdifAtt)
                                                        break
                                                        
                                                    print('Audio attenuation level not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')
                                                    
                                        elif x == '4': # HDMI Attenuation
                                            try:
                                                while True:    
                                                    attenuation = str(input('Enter HDMI Audio Attenuation, Enter 0dB -3dB -6dB -9dB -11dB: '))
                                                    if attenuation in audioAtt:
                                                        print(attenuation + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.digitalAudioLevelHdmi" '
                                                        hdmiAtt = command + attenuation
                                                        sshSettingsCommand(hdmiAtt)
                                                        break
                                                        
                                                    print('Audio attenuation level not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')
                                                    
                                        elif x == '5': # SPDIF Delay
                                            try:
                                                while True:    
                                                    spdif_time = str(input('Enter SPDIF Audio Delay, Enter 0 10 20 30 40 50 60 70 80 90 100 110 120 130 150 160 170 180 190 200: '))
                                                    if spdif_time in audioDelay:
                                                        print(spdif_time + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.audioDelay" '
                                                        spdifDelay = command + spdif_time
                                                        sshSettingsCommand(spdifDelay)
                                                        break
                                                    
                                                    print('Audio delay not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')

                                        elif x == '6': # HDMI Delay
                                            try:
                                                while True:    
                                                    hdmi_time = str(input('Enter HDMI Audio Delay, Enter 0 10 20 30 40 50 60 70 80 90 100 110 120 130 150 160 170 180 190 200: '))
                                                    if hdmi_time in audioDelay:
                                                        print(hdmi_time + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.audioDelayHdmi" '
                                                        hdmiDelay = command + hdmi_time
                                                        sshSettingsCommand(hdmiDelay)
                                                        break
                                                     
                                                    print('Audio delay not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else: 
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()
                            
                            

                            elif x == '42':
                                try:
                                    while True:
                                        options = """\n    PIN and parental controls \n                            
                             0 - read settings
                             1 - PIN entry required for programs classified
                             2 - Hide info and posters for programs classified
                             3 - PIN Entry required (for Non Classified programs)
                             4 - PIN to Purchase
                             5 - PIN Protect Kept Programs
                             6 - PIN for Foxtel IP Video
                             7 - Change iQ Name
                             8 - Change Parental PIN Number
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get tungsten.ux.parentalRating')
                                            print('0 = None 5 = PG and above 6 = M and above 7 = MA15+ and above 8 = AV15+ and above 9 = R18+')
                                            ss1 = saveSetting.replace('"tungsten.ux.parentalRating" , "', '')
                                            stbPrimary.update({"parentalRating": ss1}) #add parental Rating value to stbPrimary
                                            readSettings('settings_cli get application.mainapp.UI_SETTING_PICTURE_RATING')
                                            print('0 = None 5 = PG and above 6 = M and above 7 = MA15+ and above 8 = AV15+ and above 9 = R18+')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PICTURE_RATING" , "', '')
                                            stbPrimary.update({"UI_SETTING_PICTURE_RATING": ss1})#add picture rating value to stbPrimary
                                            readSettings('settings_cli Get "tungsten.ux.nonRatedPC"')
                                            ss1 = saveSetting.replace('"tungsten.ux.nonRatedPC" , "', '')
                                            stbPrimary.update({"nonRatedPC": ss1})  #add nonrated PC value to stbPrimary
                                            readSettings('settings_cli get application.mainapp.UI_SETTING_PIN_PURCHASE')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PIN_PURCHASE" , "', '')
                                            stbPrimary.update({"UI_SETTING_PIN_PURCHASE": ss1}) #add PIN Purchase to stbPrimary
                                            readSettings('settings_cli get application.mainapp.UI_SETTING_PIN_KEPT_PROGRAMS')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PIN_KEPT_PROGRAMS" , "', '')
                                            stbPrimary.update({"UI_SETTING_PIN_KEPT_PROGRAMS": ss1}) #add PIN Kept value to stbPrimary
                                            readSettings('settings_cli get application.mainapp.UI_SETTING_PIN_IP_VIDEO')
                                            ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_PIN_IP_VIDEO" , "', '')
                                            stbPrimary.update({"UI_SETTING_PIN_IP_VIDEO": ss1}) #add PIN IP video value to stbPrimary
                                            readSettings('settings_cli get "tungsten.ux.ParentalPincode"')
                                            ss1 = saveSetting.replace('"tungsten.ux.ParentalPincode" , "', '')
                                            stbPrimary.update({"ParentalPincode": ss1}) #add PIN Code to stbPrimary
                                          
                                        elif x == '1':
                                            try:
                                                while True:
                                                    pinEntry = str(input('Enter one of the following classifications, Enter \n 0 = None \n 5 = PG and above \n 6 = M and above \n 7 = MA15+ and above \n 8 = AV15+ and above \n 9 = R18+ \n: '))
                                                    if pinEntry in classificationAge:
                                                        print(pinEntry + ' Selected')
                                                        command = 'settings_cli set "tungsten.ux.parentalRating" '
                                                        pinEntryClass = command + pinEntry
                                                        sshSettingsCommand(pinEntryClass)
                                                        break
                                                 
                                                    print('PIN classification code is not recognised. Try again')
                                                     
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')
                                                
                                        elif x == '2':
                                            try:
                                                while True:
                                                    pictureRating = str(input('Enter one of the following classifications, Enter \n 0 = None \n 5 = PG and above \n 6 = M and above \n 7 = MA15+ and above \n 8 = AV15+ and above \n 9 = R18+ \n: '))
                                                    if pictureRating in classificationAge:
                                                        print(pictureRating + ' Selected')
                                                        sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_PICTURE_RATING','%s')"  """"" % pictureRating)
                                                        break
                                                        
                                                    print('Hide picture classification code is not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed')
                                         
                                        elif x == '3':
                                            enter = input('Enter "TRUE" to enable, or "FALSE" to disable PIN Entry required for Non Classified programs: ')
                                            nonRatedPC = str(enter)
                                            command = 'settings_cli Set "tungsten.ux.nonRatedPC" '
                                            updateNonRatedPC = command + nonRatedPC
                                            sshSettingsCommand(updateNonRatedPC)
                                            
                                        elif x == '4':
                                            enter = input('Enter "TRUE" to enable, or "FALSE" to disable PIN to Purchase: ')
                                            PINPurchase = str(enter)
                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_PIN_PURCHASE','%s')"  """"" % PINPurchase)
                                            
                                        elif x == '5':
                                            enter = input('Enter "TRUE" to enable, or "FALSE" to disable PIN Protect Kept Programs: ')
                                            PINKept = str(enter)
                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_PIN_KEPT_PROGRAMS','%s')"  """"" % PINKept)
                                            
                                        elif x == '6':
                                            enter = input('Enter "TRUE" to enable, or "FALSE" to disable PIN for Foxtel IP Video: ')
                                            ipVideo = str(enter)
                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_PIN_IP_VIDEO','%s')"  """"" % ipVideo)
                                            
                                        elif x == '7':
                                            enter = input('Enter New Name for STB: ')
                                            iQName = str(enter)
                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_STB_NAME','%s')"  """"" % iQName)
                                            print('STB name changed to ' + iQName)
                                            confirm = input('This requres a reboot of the STB to take effect, do you want to reboot now Y : ')
                                            
                                            if confirm == 'Y':
                                                stbReboot()
                                            
                                            else:
                                                print('change to STB name will take effect on next reboot')
                                                continue 
                                            
                                        elif x == '8':
                                            enter = input('Enter New PIN: ')
                                            changePIN = str(enter)
                                            command = 'settings_cli Set "tungsten.ux.ParentalPincode" '
                                            updateParentalPIN = command + changePIN
                                            sshSettingsCommand(updateParentalPIN)
                                                                       
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed.')
                                    close()
                            
                            elif x == '43':
                                try:
                                    while True:
                                        options = """ \n   Streaming and Download Settings \n                            
                             0 - read Settings
                             1 - Streaming quality
                             2 - When fast forwarding or rewinding a stream, always show
                             3 - When Downloading to Library save as
                             4 - When renting from store Download/Stream
                             5 - When watching Foxtel On Demand content Download/Stream
                             6 - Download buffer size
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_BANDWIDTH_QUALITY"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_POSTCARDS_ENABLED"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_DOWNLOAD_QUALITY"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_PPV_PLAYBACK_TYPE"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_ON_DEMAND_PLAYBACK_TYPE"')
                                            readSettings('settings_cli get "application.mainapp.UI_SETTING_BUFFER_SIZE"')
                                            print('          0 = Auto 1 = Small 3 = Medium 10 = Large \n' )
                                            
                                        elif x == '1': #Streaming Quality
                                            try:
                                                while True:    
                                                    StreamingQuality = ("best", "low")
                                                    spdif_format = str(input('Enter Spdif Audio format, best or low: '))
                                                    if spdif_format in StreamingQuality:
                                                        print(spdif_format + ' Selected')
                                                        sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_BANDWIDTH_QUALITY','%s')"  """"" % spdif_format)
                                                        break   

                                                    print('Audio format not recognised. Try again')
                                                    
                                            except KeyboardInterrupt:
                                                print('CTRL+C Pressed') 
                                        
                                        elif x == '2':                            
                                            enter = input('When fast forwarding or rewinding a stream, always show: \n Enter "true" to for postcard enable or "false" for Full Screen View: ')
                                            postcardEnabled = str(enter)
                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_POSTCARDS_ENABLED','%s')"  """"" % postcardEnabled)
                                                                            
                                        elif x == '3': #Downloading to library 
                                            print ('STB can only download in http - Current STM Mode:  ' + stbDetails["STB Mode"])
                                            modeCheck = 'dsmcc'
                                            if modeCheck in stbDetails.values():
                                                try:
                                                    while True:    
                                                        libraryQuality = ("uhd", "hd", "sd")
                                                        library_format = str(input('Enter Format for downloading to Library, uhd or hd or sd: '))
                                                        if library_format in libraryQuality:
                                                            print(library_format + ' Selected')
                                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_DOWNLOAD_QUALITY','%s')"  """"" % library_format)
                                                            break
                                                        
                                                        print('Audio format not recognised. Try again')
                                                                                            
                                                except KeyboardInterrupt:
                                                    print('CTRL+C Pressed')
                                                    
                                            else:
                                                print ('STB is in IP Mode this setting is not available')
                                            
                                        elif x == '4':
                                            print ('STB can only download in http - Current STM Mode:  ' + stbDetails["STB Mode"])
                                            modeCheck = 'dsmcc'
                                            if modeCheck in stbDetails.values():
                                                try:
                                                    while True:     
                                                        pbTypeChoosen = str(input('Enter required mode: stream or download: '))
                                                        if pbTypeChoosen in playbackType:
                                                            print(pbTypeChoosen + ' Selected')
                                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_PPV_PLAYBACK_TYPE','%s')"  """"" % pbTypeChoosen)
                                                            break
                                                            
                                                        print('Playback Type  not recognised. Try again')
                                            
                                                except KeyboardInterrupt:
                                                    print('CTRL+C Pressed')                                
                                            
                                            else:
                                                print ('STB is in IP Mode this setting is not available')
                                            
                                        elif x == '5':
                                            print ('STB can only download in http - Current STM Mode:  ' + stbDetails["STB Mode"])
                                            modeCheck = 'dsmcc'
                                            if modeCheck in stbDetails.values():
                                                try:
                                                    while True:     
                                                        pbTypeChoosen = str(input('Enter required mode: stream or download: '))
                                                        if pbTypeChoosen in playbackType:
                                                            print(pbTypeChoosen + ' Selected')
                                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_ON_DEMAND_PLAYBACK_TYPE','%s')"  """"" % pbTypeChoosen)
                                                            break
                                                            
                                                        print('Playback Type  not recognised. Try again')
                                                                                
                                                except KeyboardInterrupt:
                                                    print('CTRL+C Pressed')
                                            
                                            else:
                                                print ('STB is in IP Mode this setting is not available')
                                            
                                        elif x == '6':
                                            print ('Current STM Mode:  ' + stbDetails["STB Mode"])
                                            modeCheck = 'dsmcc'
                                            if modeCheck in stbDetails.values():
                                                bufferSize = ("0", "1", "3", "10",)
                                                try:
                                                    while True:     
                                                        bufferChoosen = str(input('Enter the required buffer size: 0 = Auto 1 = Small 3 = Medium 10 = Large: '))
                                                        if bufferChoosen in bufferSize:
                                                            print(bufferChoosen + ' Selected')
                                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_BUFFER_SIZE','%s')"  """"" % bufferChoosen)
                                                            break
                                                            
                                                        print('Playback Type  not recognised. Try again')
                                                                                
                                                except KeyboardInterrupt:
                                                    print('CTRL+C Pressed')
                                            
                                            else:
                                                print ('STB is in IP Mode this setting is not available')
                                        
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close()     
                            
                            elif x == '44':
                                try:
                                    while True:
                                        options = """    Remote Control Settings \n                            
                             0 - read 
                             1 - Voice Setting
                             2 - HDMI-CEC Control
                             3 - HDMI-CEC Volume Control
                             q - quit
                             b - back
                             """
                                        print(options)
                                        x = input('>: ')
                                        
                                        if x== '0':
                                            readSettings('settings_cli get application.mainapp.UI_SETTING_VOICE_ENABLED')
                                            readSettings('settings_cli get tungsten.ux.hdmiCecControlSetting')
                                            readSettings('settings_cli get tungsten.ux.hdmiCecVolumeControlSetting')
                                            
                                        elif x == '1':
                                            enter = input('Enter "TRUE" to enable, or "FALSE" to disable Voice Control:  ')
                                            voiceEnable = str(enter)
                                            sshSettingsCommand("""calljs "oxygen.settings.ui.set('UI_SETTING_VOICE_ENABLED','%s')"  """"" % voiceEnable)
                                            
                                        elif x == '2':
                                            enter = input('Enter "True" to enable, or "False" to disable HDMI-CEC Control: ')
                                            cecControl = str(enter)
                                            command = 'settings_cli Set "tungsten.ux.hdmiCecControlSetting" '
                                            updatehdmiCecControl = command + cecControl
                                            sshSettingsCommand(updatehdmiCecControl)
                                            
                                        elif x == '3':
                                            enter = input('Enter "True" to enable, or "False" to disable HDMI-CEC Volume Control: ')
                                            cecVolume = str(enter)
                                            command = 'settings_cli Set "tungsten.ux.hdmiCecVolumeControlSetting" '
                                            hdmiCecVolume = command + cecVolume
                                            sshSettingsCommand(hdmiCecVolume)
                                            
                                        elif x == 'q':
                                            autoWrite()
                                            close()
                                            sys.exit(0)
                                 
                                        elif x == 'b':
                                            break
                                          
                                        else:
                                            print('WARNING: {} is an unknown option. Try again'.format(x))
                                        continue
                                        
                                except KeyboardInterrupt:
                                    print('CTRL+C Pressed. Shutting Down')
                                    close() 

                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()

                elif x == '50':
                    try:
                        while True:
                            options = """
                    *** System Information ***
                    51 - System Details
                    52 - Software Details
                    53 - Read all settings \n
                    b - back
                    q - quit\n 
                  """
                            print(options)
                            x = input('>: ')
                        
                            if x == '51': # System details
                                sshRespCommand('date', debug)
                                model_type()
                                getCDSN()
                                print('IP Address: ' + ip)
                                stbMacAddr()
                                getSerialNumber()
                                getMode()
                                continue
                                
                            elif x == '52': # software Details
                                sshRespCommand('date', debug)                
                                SoftwareDetails()
                                #print('Software Version:' + softwareVer + '    Build Version:' + buildVer)
                                print('EPG Software Version')
                                readSettings('settings_cli get tungsten.reporting_service.applicationVersion')
                                continue

                            elif x == '53':
                                settingsRead()
                                if args.debug:
                                    print(stbDetails)
                                    print(stbPrimary)

                            elif x == '54':
                                print (stbDetails)
                        
                            elif x == '55':
                                print (stbPrimary)
                                for x, y in stbPrimary.items():
                                    print(x,':', y)

                            elif x == '56':
                                #print (mySTBs)
                                for STB in mySTBs:
                                    print(mySTBs[STB], '\n')
                                
                            elif x == '57':
                                print(stbDetails, '\n', stbPrimary, '\n', mySTBs)

                            elif x == '59':
                                readSettings('settings_cli get "application.mainapp.UI_SETTING_TIMEOUT_LENGTH"')
                                print(f'"{saveSetting}" contains "{noSetting}" = {noSetting in saveSetting}')
                                if 'Error:key' in saveSetting:
                                    print ("No saved setting") 
                                else:
                                    print ("Saving setting")
                                    ss1 = saveSetting.replace('"application.mainapp.UI_SETTING_TIMEOUT_LENGTH" , "', '')
                                    print ('ss1' + ss1)
                                    stbPrimary.update({"screenSaverTimeout": ss1})
                                                                    
                            elif x == '58':
                                updateMySTB()

                            elif x == '60':
                                print(defaultSettings)                            

                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)

                            elif x == 'b':
                                break

                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))

                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close()
                                                                           
                elif x == '200':
                    try:
                        while True:
                            options = """   Title Blank TBC \n                            
                 0 - read 
                 1 - Enable
                 q - quit
                 b - back
                 """
                            print(options)
                            x = input('>: ')
                            
                            if x== '0':
                                sshSettingsCommand('settings_cli get tungsten.watermark.profile')
                                
                            elif x == '1':
                                sshSettingsCommand('settings_cli get tungsten.watermark.profile')
                                print('enable')
                                
                            elif x == 'q':
                                autoWrite()
                                close()
                                sys.exit(0)
                     
                            elif x == 'b':
                                break
                              
                            else:
                                print('WARNING: {} is an unknown option. Try again'.format(x))
                            continue
                            
                    except KeyboardInterrupt:
                        print('CTRL+C Pressed. Shutting Down')
                        close() 
                
                elif x == '201': 
                    continue
     
                elif x == 's':
                    writeToFile()
                    continue
                
                elif x == 'q':
                    autoWrite()
                    close()
                    sys.exit(0)
                    
                elif x == 'r':
                    stbReboot()

                else:
                    print('WARNING: {} is an unknown option. Try again'.format(x))
                continue

        except KeyboardInterrupt:
            print('CTRL+C Pressed. Shutting Down')
            close()

if __name__ == '__main__':
    main()
    