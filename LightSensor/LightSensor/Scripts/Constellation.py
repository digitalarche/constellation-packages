﻿'''
 Constellation Python proxy
 Web site: http://www.myConstellation.io
 Copyright (C) 2014-2019 - Sebastien Warin <http://sebastien.warin.fr> 
 Licensed to Constellation under one or more contributor
 license agreements. Constellation licenses this file to you under
 the Apache License, Version 2.0 (the "License"); you may
 not use this file except in compliance with the License.
 You may obtain a copy of the License at
 
 http://www.apache.org/licenses/LICENSE-2.0
 
 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied. See the License for the
 specific language governing permissions and limitations
 under the License.
'''

__version__ = '1.8.6.19032' # Last update: 4 Feb 2019
__author__ = 'Sebastien Warin <http://sebastien.warin.fr>'

import inspect, json, sys, os, time, uuid, re, zmq
from collections import namedtuple
from enum import Enum
from threading import Thread

print("Starting '{}' with the Constellation Python proxy {} on Python {} (platform {}) from '{}'".format(os.path.relpath(sys.argv[0], os.getcwd()), __version__, sys.version, sys.platform, sys.executable))

if(sys.version_info.major < 3):
    reload(sys)
    sys.setdefaultencoding("utf-8")

class MessageScope(Enum):
    none = 0
    group = 1
    package = 2
    sentinel = 3
    others = 4
    all = 5

global IsRunning
global Settings
global OnExitCallback
global OnSettingsUpdated
global OnConnectionChanged
global OnLastStateObjectsReceived
global HasControlManager
global IsConnected
global IsStandAlone
global SentinelName
global PackageName
global PackageInstanceName
global PackageVersion
global PackageAssemblyVersion
global ConstellationClientVersion
global LastStateObjects

IsRunning = False
Settings = None
OnExitCallback = None
OnSettingsUpdated = None
OnConnectionChanged = None
OnLastStateObjectsReceived = None
HasControlManager = None
IsConnected = None
IsStandAlone = None
SentinelName = None
PackageName = None
PackageInstanceName = None
PackageVersion = None
PackageAssemblyVersion = None
ConstellationClientVersion = None
LastStateObjects = None

_exitCode = None
_messageCallbacks = []
_stateObjectCallbacks = []
_messageCallbacksList = {}
_stateObjectCallbacksList = {}
_ctx = zmq.Context()
_socket = _ctx.socket(zmq.PAIR)
_socket.linger = 1000 #ms
_socket.connect("tcp://127.0.0.1:" + str(int(sys.argv[1])))
time.sleep(1.0)
_poller = zmq.Poller()
_poller.register(_socket, zmq.POLLIN)
_socket.send_string("Init")

def ConvertJsonToObject(data, tupleName = 'X', onTupleCreated = None):
    def _json_object_hook(d):
        tuple = namedtuple(tupleName, list(d.keys()))
        if onTupleCreated:
            onTupleCreated(tuple)
        return tuple(*list(d.values())) 
    return json.loads(json.dumps(data) if isinstance(data, dict) else data, object_hook=_json_object_hook)

def MessageCallback(key = None, isHidden = False):
    def _registar(func):
        _messageCallbacksList[func.__name__] = { 'Func': func, 'Key' : key, 'DeclareCallback' : not isHidden }
        return func
    return _registar

def StateObjectLink(sentinel = '*', package = '*', name = '*', type ='*'):
    def _registar(func):
        _stateObjectCallbacksList[func.__name__] = { 'Func': func, 'Sentinel' : sentinel, 'Package' : package, 'Name' : name, 'Type' : type }
        return func
    return _registar

def WriteInfo(msg):
    WriteLog('Info', msg)

def WriteWarn(msg):
    WriteLog('Warn', msg)

def WriteError(msg):
    WriteLog('Error', msg)

def WriteLog(level, msg):
    _socket.send_json({ 'Function' : 'WriteLog', 'Level' : level, 'Message' : str(msg) })

def PushStateObject(name, value, soType = None, metadatas = {}, lifetime = 0):
    _socket.send_json({ 'Function' : 'PushStateObject', 'Name': str(name), 'Value': value, 'Type': str(soType) if soType else type(value).__name__, 'Metadatas' : metadatas, 'Lifetime' : lifetime })

def SendMessage(to, key, value, scope = MessageScope.package):
    _socket.send_json({ 'Function' : 'SendMessage', 'Scope':  scope.value, 'To' : str(to), 'Key': str(key), 'Value' : value, 'SagaId' : '' })

def SendMessageWithSaga(callback, to, key, value, scope = MessageScope.package):
    sagaId = str(uuid.uuid1())
    def _msgCallback(k, context, data):
        if(k == "__Response" and context.SagaId == sagaId):
            if not data:
                callback(context) if (callback.__code__.co_argcount > 0 and callback.__code__.co_varnames[callback.__code__.co_argcount - 1] == 'context') else callback()
            else:
                if isinstance(data, list):
                    if (callback.__code__.co_argcount > 0 and callback.__code__.co_varnames[callback.__code__.co_argcount - 1] == 'context'):
                        data.append(context)
                    callback(*data)
                else:
                    callback(data, context) if (callback.__code__.co_argcount > 0 and callback.__code__.co_varnames[callback.__code__.co_argcount - 1] == 'context') else callback(data)
            _messageCallbacks.remove(_msgCallback)
    _messageCallbacks.append(_msgCallback)
    _socket.send_json({ 'Function' : 'SendMessage', 'Scope':  scope.value, 'To' : str(to), 'Key': str(key), 'Value' : value, 'SagaId' : sagaId })

def SubscribeMessages(group):
    _socket.send_json({ 'Function' : 'SubscribeMessages', 'Group' : str(group) })

def UnSubscribeMessages(group):
    _socket.send_json({ 'Function' : 'UnSubscribeMessages', 'Group' : str(group) })
    
def RefreshSettings():    
    _socket.send_json({ 'Function' : 'GetSettings' })

def RequestStateObjects(sentinel = '*', package = '*', name = '*', type ='*'):
    _socket.send_json({ 'Function' : 'RequestStateObjects', 'Sentinel' : sentinel, 'Package' : package, 'Name' : name, 'Type' : type })

def SubscribeStateObjects(sentinel = '*', package = '*', name = '*', type ='*'):
    _socket.send_json({ 'Function' : 'SubscribeStateObjects', 'Sentinel' : sentinel, 'Package' : package, 'Name' : name, 'Type' : type })

def PurgeStateObjects(name = '*', type ='*'):
    _socket.send_json({ 'Function' : 'PurgeStateObjects', 'Name' : name, 'Type' : type })

def RegisterStateObjectLinks():
    for key in _stateObjectCallbacksList:
        soLink = _stateObjectCallbacksList[key]
        RegisterStateObjectCallback(soLink['Func'], soLink['Sentinel'], soLink['Package'], soLink['Name'], soLink['Type'])

def RegisterStateObjectCallback(func, sentinel = '*', package = '*', name = '*', type ='*', request = True, subscribe = True):
    def _soCallback(stateobject):
        if((sentinel == stateobject.SentinelName or sentinel == '*') and (package == stateobject.PackageName or package == '*') and (name == stateobject.Name or name == '*') and (type == stateobject.Type or type == '*')):
            func(stateobject)
    _stateObjectCallbacks.append(_soCallback)
    if request == True:
        RequestStateObjects(sentinel, package, name, type)
    if subscribe == True:
        SubscribeStateObjects(sentinel, package, name, type)

def GetSetting(key):
    _getSettingSync()
    if key in Settings:
        return Settings[key]
    else:
        return None

def RegisterMessageCallbacks():
    for key in _messageCallbacksList:
        func = _messageCallbacksList[key]['Func']
        RegisterMessageCallback(_messageCallbacksList[key]['Key'] if _messageCallbacksList[key]['Key'] else func.__name__, func, _messageCallbacksList[key]['DeclareCallback'], str(func.__doc__) if func.__doc__ else '')

def RegisterMessageCallback(key, func, declareCallback = False, description = '', returnType = None):
    # Message callback
    def _msgCallback(k, context, data):
        if(k == key):
            returnValue = None
            if not data:
                returnValue = func(context) if (func.__code__.co_argcount > 0 and func.__code__.co_varnames[func.__code__.co_argcount - 1] == 'context') else func()
            else:
                if isinstance(data, list):
                    if (func.__code__.co_argcount > 0 and func.__code__.co_varnames[func.__code__.co_argcount - 1] == 'context'):
                        data.append(context)
                    returnValue = func(*data)
                else:
                    returnValue = func(data, context) if (func.__code__.co_argcount > 0 and func.__code__.co_varnames[func.__code__.co_argcount - 1] == 'context') else func(data)
            if context.IsSaga and returnValue != None:
                SendResponse(context, returnValue)
    # Generate the MC Descriptor
    mcDescriptor = { 'Description': '', 'Arguments': {} }
    for argName in inspect.getargspec(func).args:
        mcDescriptor['Arguments'][argName] = {}
    for line in description.splitlines():
        if line:
            line = line.strip()
            if line:
                if line.startswith(':'):
                    line_data = re.search(':\s*([\w]+)\s*([\w]*)\s*([\w]*)\s*:\s*([^\n\r\[]*)(\[(?i)default:\s*\"*([^\"]*)\"*\])?', line)
                    if line_data:
                        line_type = line_data.group(1).strip().lower()
                        if line_type == 'param':
                            propName = line_data.group(3).strip() if line_data.group(3) else line_data.group(2).strip()
                            if propName in mcDescriptor['Arguments']:
                                mcDescriptor['Arguments'][propName]['Description'] = line_data.group(4).strip()
                                if line_data.group(3):
                                    mcDescriptor['Arguments'][propName]['Type'] = line_data.group(2).strip()
                                if line_data.group(6):
                                    mcDescriptor['Arguments'][propName]['DefaultValue'] = line_data.group(6).strip()
                        elif line_type == 'type' and line_data.group(2).strip() in mcDescriptor['Arguments']:
                             mcDescriptor['Arguments'][line_data.group(2).strip()]["Type"] = line_data.group(4).strip()
                        elif line_type == 'return' and not ('ReturnType' in mcDescriptor):
                             mcDescriptor['ReturnType'] = { 'Description' : line_data.group(4).strip() }
                             if line_data.group(2):
                                mcDescriptor['ReturnType']['Type'] = line_data.group(2).strip()
                        elif line_type == 'rtype' and 'ReturnType' in mcDescriptor:
                             mcDescriptor['ReturnType']['Type'] = line_data.group(4).strip()
                else:
                    mcDescriptor['Description'] =  mcDescriptor['Description'] + ('\n' if mcDescriptor['Description'] != '' else '') + line
    # Register the MC to the host
    _socket.send_json({ 'Function' : 'RegisterMessageCallback', 'Key' : str(key), "DeclareCallback": bool(declareCallback), 'Descriptor' : mcDescriptor })
    _messageCallbacks.append(_msgCallback)

def DescribeStateObjectType(name, description, properties):
    _socket.send_json({ 'Function' : 'DescribeType', 'Type': 'StateObject', 'TypeName' : str(name), "Description": str(description), 'Properties' : properties })

def DescribeMessageCallbackType(name, description, properties):
    _socket.send_json({ 'Function' : 'DescribeType', 'Type': 'MessageCallback', 'TypeName' : str(name), "Description": str(description), 'Properties' : properties })

def DeclarePackageDescriptor():
    _socket.send_json({ 'Function' : 'DeclarePackageDescriptor' })

def SendResponse(context, value):
    if not context:    
        WriteError("Invalid context")
    elif not context.IsSaga:
        WriteError("No Saga on this context")
    else:
       _socket.send_json({ 'Function' : 'SendMessage', 'Scope':  MessageScope.package.value, 'To' : context.Sender.ConnectionId if context.Sender.Type == 0 else context.Sender.FriendlyName, 'Key': '__Response', 'Value' : value, 'SagaId' : context.SagaId })

def Shutdown():
    _socket.send_json({ 'Function' : 'Shutdown' })

def _onReceiveMessage(key, context, data):
    try:
        for mc in _messageCallbacks:
            mc(key, context, data)
    except Exception as e:
        WriteError("Error while dispatching message '%s': %s" % (key, str(e)))

def _onStateObjectUpdated(stateObject):
    try:
        for callback in _stateObjectCallbacks:
            callback(stateObject)
    except Exception as e:
        WriteError("Error while dispatching StateObject : %s" % str(e))

def _exit(exitCode = 0):
    global IsRunning
    global _exitCode
    WriteWarn("Exiting %s with code:%s" % (sys.argv[0], exitCode))
    if OnExitCallback:
        try:
            OnExitCallback(exitCode)
        except:
            pass
    time.sleep(0.1) 
    if _exitCode == 0:
        _exitCode = exitCode
        IsRunning = False
    else:
        IsRunning = False
        sys.exit(exitCode)

def _getSettingSync():
    global Settings
    if(Settings is None):
        ts = _getCPUtime()
        RefreshSettings()
        while Settings is None and (_getCPUtime() - ts) < 30:
            try:
                socks = dict(_poller.poll(1000))
                if socks:
                    message = _socket.recv_json()
                    if message['Type'] == "SETTINGS":
                        Settings = message['Settings']
                        return
            except Exception as e:
                WriteError("Unable to get setting : %s" % str(e))
            time.sleep(0.1)

def _getCPUtime():
    if(sys.version_info.major >= 3 and sys.version_info.minor >= 3):
        return time.process_time() 
    else:
        return time.clock()

def _runAsync(targetFunction, args = None):
    t1 = Thread(target = targetFunction, args = args)
    t1.start()

def _dispatcherMessage():
    global Settings
    global HasControlManager
    global IsConnected
    global IsStandAlone
    global SentinelName
    global PackageName
    global PackageInstanceName
    global PackageVersion
    global PackageAssemblyVersion
    global ConstellationClientVersion
    global LastStateObjects
    lastPing = _getCPUtime()
    while IsRunning:
        try:
            socks = dict(_poller.poll(1000))
            now = _getCPUtime()
            if ((now - lastPing) >= 30):
                WriteError("No ping from the Package Host since %s seconds" % int(now - lastPing))
                _exit(2)
                break
            if socks:
                message = _socket.recv_json()
                if message['Type'] == "PING":
                    lastPing = _getCPUtime()
                    _socket.send_string("PONG")
                elif message['Type'] == "PACKAGESTATE":
                    HasControlManager = message['HasControlManager']
                    IsConnected = message['IsConnected']
                    IsStandAlone = message['IsStandAlone']
                    SentinelName = message['SentinelName']
                    PackageName = message['PackageName']
                    PackageInstanceName = message['PackageInstanceName']
                    PackageVersion = message['PackageVersion']
                    PackageAssemblyVersion = message['PackageAssemblyVersion']
                    ConstellationClientVersion = message['ConstellationClientVersion']
                elif message['Type'] == "LASTSTATEOBJECTS":
                    LastStateObjects = []
                    for so in message['StateObjects']:
                        LastStateObjects.append(ConvertJsonToObject(so, 'StateObject'))
                    if OnLastStateObjectsReceived:
                        try:
                            _runAsync(OnLastStateObjectsReceived)
                        except Exception as e:
                            WriteError("Error while invoking the OnLastStateObjectsReceived event handler : %s" % str(e))
                elif message['Type'] == "CONNECTIONSTATE":
                    IsConnected = message['IsConnected']
                    if OnConnectionChanged:
                        try:
                            _runAsync(OnConnectionChanged)
                        except Exception as e:
                            WriteError("Error while invoking the OnConnectionChanged event handler : %s" % str(e))
                elif message['Type'] == "MSG":
                    def _addSendResponse(tuple):
                        tuple.SendResponse = lambda ctx, rsp: SendResponse(ctx, rsp)
                    context = ConvertJsonToObject(message['Context'], 'MessageContext', _addSendResponse)
                    args = ()
                    if 'Data' in message:
                        try:
                            data = ConvertJsonToObject(message['Data'])
                        except:
                            data = message['Data']
                        args = (message['Key'], context,  data)
                    else:
                        args = (message['Key'], context, "")
                    _runAsync(_onReceiveMessage, args)
                elif message['Type'] == "SETTINGS":
                    Settings = message['Settings']
                    if OnSettingsUpdated:
                        try:
                            _runAsync(OnSettingsUpdated)
                        except Exception as e:
                            WriteError("Error while invoking the OnSettingsUpdated event handler : %s" % str(e))
                elif message['Type'] == "STATEOBJECT":
                    try:
                        so = ConvertJsonToObject(message['StateObject'], 'StateObject')
                    except Exception as e:
                        WriteError("Unable to deserialize the StateObject : %s" % str(e))
                    _runAsync(_onStateObjectUpdated, [so])
                elif message['Type'] == "EXIT":
                    _exit(0)
                    break
        except Exception as e:
            WriteError("Internal loop error : %s" % str(e))

def Start(onStart = None):
    global _exitCode
    _exitCode = 0
    StartAsync()
    if onStart:
        msgCb = len(_messageCallbacks)
        try:
            onStart()
        except Exception as e:
            WriteError("Fatal error: %s" % str(e))
            _exit(1)
        if len(_messageCallbacks) > msgCb:
            DeclarePackageDescriptor()
    while IsRunning:
        time.sleep(0.1)
    if _exitCode:
        sys.exit(_exitCode)

def StartAsync():
    global IsRunning
    RegisterStateObjectLinks()
    RegisterMessageCallbacks()
    if len(_messageCallbacks) > 0:
        DeclarePackageDescriptor()
    t1 = Thread(target = _dispatcherMessage)
    t1.setDaemon(True)
    IsRunning = True
    t1.start()
    RefreshSettings()
    while IsRunning and Settings is None:
        time.sleep(1.0)
