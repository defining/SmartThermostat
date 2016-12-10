/*
 ******************************************************************************
 *
 *  Université libre de Bruxelles
 *  TRAN-H-201 - Projet informatique II
 *  Arduino/ESP8266-based thin thermostat
 *  Author: Stefan Eppe (2015)
 * 
 * ----------------------------------------------------------------------------
 * 
 *  This sketch allows using an Arduino coupled with an ESP8266-01 wifi as a 
 *  thin thermostat. Due to the very limited memory available on an ATmega328
 *  microcontroller-based board, the features of the provided functions are 
 *  minimalistic and specifically tailored to meet the requirements of the 
 *  assignment.
 * 
 *  The provided functionalities are:
 *   - serial, AT-command-based interface with an ESP8266 wifi module, using 
 *     TTL serial communication (according to the communication protocol 
 *     described in the project's assignment)
 *   - temperature and presence sensing
 *   - valve actuator (throug 0-5V output signal)
 *   - registration of the thin thermostat to the central one
 *  
 * ----------------------------------------------------------------------------
 * 
 *  Hardware specifications:
 *   - Arduino Nano (ATmega328) clocked at 16MHz
 *   - ESP8266-01 module with v0.9.2.2 firmware
 *   - 10kOhm NTC thermistor (see connection below)
 *   - Passive infrored (PIR) sensor  
 *   
 * ----------------------------------------------------------------------------
 * 
 *  CAUTION: Only some functions below are to be modified. The functions that 
 *  are not explicitly required to be changed should not be altered in any way.
 *
 *  Functions to be modified are in the following sections below:
 *    - SENSORS-INTERACTION FUNCTIONS
 *    - COMMUNICATION PROTOCOL FUNCTIONS
 *    - MAIN CODE
 *
 ******************************************************************************
*/


// ======== Compilation flags ==========

#define DEBUG                          // Uncomment to switch debugging on
//#define ECHO                         // Uncomment to switch command echoing on


// ---- Device software settings -------

#define DEVICE_TYPE    F("thin")       // Possible values: "thin" and "outside"

#define NETWORK_SSID   "TRANH201-G01"  // Todo: adapt to your group's ssid
#define NETWORK_PASSWD ""              // Leave empty (open network)

#define SERVER_IP      "192.168.10.1"  // IP and port of the central thermostat
#define SERVER_PORT    "8080"          // (adapt if necessary)

#define LISTEN_PORT    "9000"          // Port the device is listening on when
                                       // in server mode (after registration)

// ---- Device hardware settings -------

#define THERMISTOR_ANALOG_PIN   4      // Todo: adapt the pins to your setup
#define PIR_DIGITAL_PIN         11       
#define VALVE_ANALOG_PIN        5


// ---- Help constants -----------------

#define CONTINUE    false
#define HALT        true


// ---- Includes -----------------------

//#ifdef DEBUG
  #include <SoftwareSerial.h>
  SoftwareSerial dbg(8,9);
//#endif


// ---- Global variables ---------------

// Todo: Put the possible global values here.




/*
 ******************************************************************************
 *  HELPER FUNCTIONS
 *  DO NOT MODIFY
 ******************************************************************************
*/


void debug(const String& cmd)
{
  #ifdef DEBUG
    dbg.print( cmd );
  #endif
}

void debug(char c)
{
  #ifdef DEBUG
    dbg.print( c );
  #endif
}

void debugln(const String& cmd)
{
  debug(cmd + "\r\n");
}


void halt(const String& msg)
{
  debugln(msg);
  while( 1 );
}



/*
 ******************************************************************************
 *  SENSORS-INTERACTION FUNCTIONS
 *  YOU NEED TO COMPLETE FUNCTIONS IN THIS SECTION
 ******************************************************************************
*/


// ---- Thermistor ---------------------

float readThermistor()
{
  // Todo: Complete the code to return the currently sensed temperature.
  return 0.0;
}


// ---- Presence sensor (PIR) ----------

boolean readPirState()
{
  // Todo: Complete the code to return the sensed presence.
  return false;
}


// ---- Actuation valve ----------------

int readValve()
{
  // Todo: Complete the code to return the current valve setting (0-100).
  return 0;
}

int setValve(int value)
{
  // Todo: Complete the code to set the current valve setting (0-100).
}



/*
 ******************************************************************************
 *  ESP8266 INTERACTION FUNCTIONS
 *  DO NOT MODIFY
 ******************************************************************************
 *  The code below has been mainly adapted from the following internet 
 *  resources:
 *   - https://gist.github.com/prasertsakd/5c5deb80e37344250cc1
 *   - https://gist.github.com/xesscorp/3f791cdec611db3eb400
 ******************************************************************************
*/


// Get the data from the WiFi module and send it to the debug serial port
String espGetResponse(const String& cmd, int timeOut = 1000)
{
  String resp;
  long deadline = millis() + timeOut;

  Serial.println(cmd);
  delay(500);
  while (Serial.available() > 0 || millis() < deadline )  {
    if( Serial.available() ) {
      resp += char(Serial.read());  
      delay(50); 
      if ( resp.indexOf(cmd) > -1 )         
        resp = "";
      else
        resp.trim();       
    }
  }  

  return resp;
}


// Overload of espGetResponse() to add a delay prior to sending the command to the wifi module
String espGetResponse(int preDelay, String cmd, int timeOut = 1000)
{
  delay(preDelay);
  return espGetResponse(cmd, timeOut);
}



// Read characters from WiFi module and echo to serial until keyword occurs or timeout.
boolean espWaitAcknowledge(const String& keyword, int timeOut = 1000)
{
  byte current_char = 0;
  byte keyword_length = keyword.length();
  
  // Fail if the target string has not been sent by deadline.
  long deadline = millis() + timeOut;
  while( millis() < deadline )
  {
    if (Serial.available())
    {
      char ch = Serial.read();
      delay(1);
      #ifdef ECHO
         dbg.print(ch);
      #endif      
      if (ch == keyword[current_char])
        if (++current_char == keyword_length)
          return true;
    }
  }
  return false;  // Timed out
}


// (Used when we're indifferent to "OK" vs. "no change" responses or 
// to get around firmware bugs.)
String espClearBuffer() 
{
  String res = "";
  char flushedChar;
  while(Serial.available()){ 
    flushedChar = Serial.read();
    res += flushedChar;
    delay(5);
  }
  return res;
}


// Send a command to the module and wait for acknowledgement string
// (or flush module output if no ack specified).
boolean espCmd(const String& cmd, const String& ack = "", 
               boolean haltOnFail = false, int timeOut = 1000)
{
  espClearBuffer();
      
  Serial.println(cmd);
  delay(100);
    
  // If no specified, wait for ack.
  if( !( ack == "" || espWaitAcknowledge(ack, timeOut) ) && haltOnFail) {
      halt(F("No response from module"));
  }
  
  return true;
}

// Overload of espCmd() to add a delay prior to sending the command to the 
// wifi module (used for chaining the commands with "&&", e.g., in espInit() )
boolean espCmd(int preDelay, 
               const String& cmd, const String& ack = "", 
               boolean haltOnFail = false, int timeOut = 1000)
{
  delay( preDelay );
  return espCmd( cmd, ack, haltOnFail, timeOut );  
}


// ============================================================================


boolean espPresent()
{
  return espCmd( F("AT"), F("OK") );
}


boolean espInit()
{
  return    espCmd(        F("AT+CWMODE=1"),    F("")       )
         && espCmd(  100,  F("AT+RST"),         F("ready")  )
         && espCmd(  200,  F("AT+CIPMUX=1"),    F("OK")     )
         && espCmd(  100,  F("AT+CIPSTO=1000")              );
}


boolean espInitAsServer()
{
  debugln("starting server");
  return espCmd( 100, String("AT+CIPSERVER=1,")+LISTEN_PORT,    F("OK")       );
}


boolean espWifiConnect()
{
  return espCmd( 200,  
                 String("AT+CWJAP=\"")+NETWORK_SSID+"\",\""+NETWORK_PASSWD+"\"",  
                 F("OK"),  HALT,  20000 );
}


String espIP()
{
  String ip = espGetResponse( 200, F("AT+CIFSR"), 1000 );
  return ip.substring(0,ip.length()-2);
}


// ----- ----- ----- ----- ----- ----- ----- ----- ----- 


// minimalistic http request mechanism
// returns the http response code (message and body are lost)
int sendHttpRequest( const String& req, const String& host = SERVER_IP, 
                     const String& port = SERVER_PORT)
{
  espClearBuffer();
  espCmd( 50, F("AT+CIPCLOSE") ); // just to make sure there isn't any open connection
  
  boolean resp =   
       espCmd(  100,  "AT+CIPSTART=0,\"TCP\",\"" + host + "\"," + port,     F("OK") )
    && espCmd(  500,  "AT+CIPSEND=0,"+String(req.length()),                 F(">")  )
    && espCmd(  200,  req , F(":HTTP/") );

  delay(50);

  // Use of local variable seems to work better than using espClearBuffer()
  //  in the return expression.
  String tmp = espClearBuffer();

  return resp ? tmp.substring(4,7).toInt() : -1;
}


boolean serveRawContent(const String& content) 
{
  // FixMe: We hardcode the channel to 0 here, but the one returned
  //        from the server (after the "+IPD:") should be used instead.
  return    espCmd( "AT+CIPSEND=0," + String(content.length()) , ">" )
         && espCmd( 200, content );
}

void serveHttpBadRequest()
{
  serveRawContent( "HTTP/1.0 400 BAD REQUEST\r\nConnection: close\r\nContent-Length:0\r\n\r\n" );
}

void serveHttpOK()
{
  serveRawContent( "HTTP/1.0 200 OK\r\nConnection: close\r\nContent-Length:0\r\n\r\n" );
}
       
void serveHttpContent(const String& ContentType, const String& Content) 
{  
  serveRawContent(   "HTTP/1.0 200 OK\r\nContent-Type: " + ContentType + "\r\n"
                   + "Connection: close\r\n"
                   + "Content-Length: " + String(Content.length()) + "\r\n"
                   + "\r\n"
                   + Content
                   + "\r\n");
}
  
void serveHtmlContent(const String& Content) {
  serveHttpContent(F("text/html"), Content);
}       


String httpServerListen()
{
  Serial.setTimeout(500);
  if( espWaitAcknowledge("+IPD,", 100) ) {
    delay(100);
    String tmp = espClearBuffer();
    delay(100);
    return tmp.substring(tmp.indexOf(':')+1);
  }
  return "";
}




/*
 ******************************************************************************
 *  COMMUNICATION PROTOCOL FUNCTIONS
 *  YOU NEED TO COMPLETE FUNCTIONS IN THIS SECTION
 ******************************************************************************
 */


void serveTemperature()
{
  // Todo: Adapt to serve the current temperature reading according to the 
  //       communication protocol.
}

void servePresence()
{
  // Todo: Adapt to serve the current presence reading according to the 
  //       communication protocol.
}

void serveValveGet()
{
  // Todo: Adapt to serve the current valve setting according to the 
  //       communication protocol.
}


// DEVICE REGISTRATION - DO NOT MODIFY

boolean registerDevice()
{
  char buf[5]; // "NNNN\0"
  String cmd = "{\"ip\":\"" + espIP() + "\",\"port\":" + LISTEN_PORT + ",\"type\":\""+ DEVICE_TYPE + "\"}\r\n";
  int len = cmd.length();
  cmd =   "PUT /register HTTP/1.0\nContent-Type:application/json\r\nContent-Length: "
        + String(itoa(len,buf,10)) + "\r\n\r\n" + cmd + "\r\n";

  int res = sendHttpRequest(cmd);
 
  return res == 200;
}


boolean startDeviceServer()
{
  return espInitAsServer();
}


/*
 ******************************************************************************
 * MAIN CODE
 * COMPLETE AS NECESSARY
 ******************************************************************************
 */



void setup()
{ 
  Serial.begin(9600); 

  #ifdef DEBUG
    dbg.begin(9600);
    debugln("\r\n*** Thin thermostat debug ****");
  #endif

  if( espPresent() )     debugln(F("module found"));
                         else halt(F("wifi module not found!"));

  if( espInit() )        debugln(F("wifi initialized"));
                         else halt(F("Wifi module initialisation failure."));

  if( espWifiConnect() ) debugln("connected to network (ip="+espIP()+")" );
                         else halt(F("Could not connect to network."));

  if( registerDevice() ) debugln(F("device registered"));
                         else halt(F("device registration error"));

  if( startDeviceServer() ) debugln(F("rest server started"));
                         else halt(F("server initialisation error"));
}


boolean isInstruction(const String& cmdLine, const String& cmdSearched)
{
  return ( cmdLine.substring(0,cmdSearched.length()) == cmdSearched );
}


void loop()
{
  String cmd;
  int counter = 100;
  
  while(1)
  {   
    cmd = httpServerListen();
    
    if( isInstruction(cmd, F("GET /temperature ")) ) {
      serveTemperature();
    }
    else 
    if( isInstruction(cmd, F("GET /presence ")) ) {
      servePresence();
    }
    else 
    if( isInstruction(cmd, F("GET /valve ")) ) {
      serveValveGet();
    }      
    else
    if( isInstruction(cmd, F("PUT /valve?value=")) ) {
      cmd = cmd.substring(17,cmd.indexOf('H')-1);
      int value = cmd.toInt();  // "value" contains the new value for the valve
      // Todo: Complete to actuate/update according to the valve value.
    }    
  }
}

