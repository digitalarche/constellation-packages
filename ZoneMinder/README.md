# ZoneMinder connector for Constellation

Connect your ZoneMinder (>= 1.29) video security system to Constellation.

Documentation : https://developer.myconstellation.io/package-library/zoneminder/

### MessageCallbacks
 - Restart() : Restarts ZoneMinder.
 - ChangeState(State state) : Changes the state of ZoneMinder.
 - ForceAlarm(int monitorId) : Forces the alarm.
 - CancelForcedAlarm(int monitorId) : Cancels the forced alarm.
 - SetMonitorFunction(int monitorId, MonitorFunction function, bool enabled) : Sets the monitor function.
 - GenerateStreamingURI(int id, StreamingOptions.Source source, StreamingOptions.Mode mode, StreamingOptions options) : Generates the streaming URI for live or pre-recorded streams.
 - SearchEvents(EventSearchCriterias criteria) : Searches events with one criteria.
 - SearchEventsWithMultiCriterias(EventSearchCriterias[] criterias) : Searches events with criterias.
 - GetEvent(int eventId) : Gets event by ID.
 - UpdateEvent(int eventId, UpdateEventRequest request) : Updates the event.
 - DeleteEvent(int eventId) : Deletes the event.

**Note** : when your ZoneMinder recorded a new event, the package sent the `Event` data in a message named `OnZoneMinderEvent` to the Constellation group `ZoneMinder`. You can change the group name with the setting `EventsGroupName`.

So you can write a piece of code in Arduino, Javascript, .NET, Python and more that handles a ZoneMinder event. For example, in Javascript :

```javascript
constellation.registerMessageCallback("OnZoneMinderEvent", function (msg) {
    console.log("ZoneMinder event : ", msg.Data);
});
constellation.subscribeMessages("ZoneMinder");
```


### StateObjects
 - Host : represent your ZoneMinder host (URI, version, CPU load, disk usage, daemon check, etc..) 
 - One StateObject per monitor (ID, name, type, monitor function, state, fps, events and more)
   - Type of `ZoneMinder.Monitor` for ZM 1.29/1.30 and `ZoneMinder.Monitor2` for 1.32 and above

### Installation

Declare the package in a Sentinel with the following configuration.

* If you have ZM >= 1.32, use the login API easily like this :

```xml
<package name="ZoneMinder">
  <settings>
    <add key="RootUri" value="http://zoneminder" />
    <add key="UseLoginAPI" value="true" />
    <add key="Username" value="admin" />
    <add key="Password" value="password" />
  </settings>
</package>
```

* Otherwise if you have an older version of ZM (1.29-1.31), use the PasswordHash and SecretHash :

```xml
<package name="ZoneMinder">
  <settings>
    <add key="RootUri" value="http://zoneminder" />
    <add key="UseLoginAPI" value="false" />
    <add key="Username" value="admin" />
    <add key="PasswordHash" value="4F56EF3FCEF3F995F03D1E37E2D692D420111476" />
    <add key="SecretHash" value="T9TyLzZ7yJBvmKx8TyLefhVVtz8AUZXf" />
  </settings>
</package>
```

The SecretHash must be set in your ZoneMinder's options (AUTH_HASH_SECRET) and the password hash is generated by the query `SELECT PASSWORD('your password')` (you must run this query on your ZoneMinder's MySQL server).

For more information read this : https://developer.myconstellation.io/package-library/zoneminder/#Installation_du_package_Constellation

License
----

Apache License

Other
----

Not implemented (in this version 2.0 based on ZM 1.32.3) :
- PTZ stream & PTZ Control APIs
- Add/Edit/Delete a monitor
- Create a Zone
- Configuration APIs
- Monitor daemonStatus
- Multi-server & Multi-storage APIs