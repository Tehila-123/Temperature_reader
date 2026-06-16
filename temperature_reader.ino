/**
 * Temperature Reader and LCD Monitor for Arduino Uno (I2C LCD Version)
 * 
 * Part of the Embedded Systems Coursework.
 * 
 * Hardware Connections:
 * - LM35 Temp Sensor: OUT -> Analog Pin A0, VCC -> 5V, GND -> GND
 * - LCD 16x2 with I2C Module:
 *   GND -> Arduino GND
 *   VCC -> Arduino 5V
 *   SDA -> Arduino Pin A4 (or dedicated SDA pin near AREF)
 *   SCL -> Arduino Pin A5 (or dedicated SCL pin near AREF)
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ==========================================
// CONFIGURATION
// ==========================================
// Candidate name to display on the first row
const char* CANDIDATE_NAME = "Ruzindana Tehila"; 

// Pin definitions
const int TEMP_SENSOR_PIN = A0;

// I2C LCD Configuration
// 0x27 is the standard address for PCF8574. If it doesn't display text, try 0x3F.
const uint8_t LCD_I2C_ADDRESS = 0x27; 
const uint8_t LCD_COLUMNS = 16;
const uint8_t LCD_ROWS = 2;

// Timing intervals (milliseconds)
const unsigned long SCROLL_INTERVAL = 350;       // Scroll name every 350ms
const unsigned long TELEMETRY_INTERVAL = 2000;    // Read temp, update LCD, and send Serial every 2 seconds

// Initialize I2C LCD object (Address, Columns, Rows)
LiquidCrystal_I2C lcd(LCD_I2C_ADDRESS, LCD_COLUMNS, LCD_ROWS);

// State variables for non-blocking timers
unsigned long lastScrollTime = 0;
unsigned long lastTelemetryTime = 0;

// Scrolling window state
int scrollStartIndex = 0;
int nameLength = 0;

// Current temperature reading
float currentTemp = 0.0;

// ==========================================
// HELPER FUNCTIONS
// ==========================================

/**
 * Reads the voltage from the LM35 sensor on A0 and converts it to Celsius.
 * LM35 has a scale factor of 10 mV / degree Celsius.
 */
float readLM35() {
  int rawValue = analogRead(TEMP_SENSOR_PIN);
  // Convert RAW to voltage (Assuming standard 5V VCC reference)
  float voltage = rawValue * (5.0 / 1023.0);
  // Convert voltage (V) to temperature (°C)
  // 10mV/°C -> 0.01V/°C -> Temp = Voltage * 100
  float tempC = voltage * 100.0;
  return tempC;
}

/**
 * Formats and prints the candidate name on the first row.
 * Performs horizontal scrolling if the name exceeds 16 characters.
 */
void updateNameRow() {
  lcd.setCursor(0, 0);
  
  if (nameLength <= 16) {
    // Fits perfectly, display statically
    lcd.print(CANDIDATE_NAME);
    // Fill the rest of the row with spaces to clear any leftover characters
    for (int i = nameLength; i < 16; i++) {
      lcd.print(' ');
    }
  } else {
    // Name exceeds 16 characters, scroll horizontally using non-blocking windowing
    // We add 4 blank spaces between the end and the restart of the name
    int totalScrollLen = nameLength + 4;
    
    for (int col = 0; col < 16; col++) {
      int charIndex = (scrollStartIndex + col) % totalScrollLen;
      if (charIndex < nameLength) {
        lcd.print(CANDIDATE_NAME[charIndex]);
      } else {
        lcd.print(' '); // Print trailing/spacing empty slots
      }
    }
    
    // Advance starting index for the next update
    scrollStartIndex = (scrollStartIndex + 1) % totalScrollLen;
  }
}

/**
 * Updates the temperature display on the second row of the LCD.
 * Formatted cleanly with proper padding and degree symbol.
 */
void updateTemperatureRow() {
  lcd.setCursor(0, 1);
  lcd.print("Temp: ");
  
  // Format float with 1 decimal place (e.g., "24.5")
  lcd.print(currentTemp, 1);
  
  // Print degree symbol (char 223 in HD44780 standard font)
  lcd.print((char)223);
  lcd.print("C");
  
  // Fill the rest of the LCD line (16 chars) with spaces to clear trailing digits
  // "Temp: " (6) + e.g. "24.5" (4) + "°" (1) + "C" (1) = 12 characters.
  // We write 4 spaces to reach 16 characters.
  lcd.print("    ");
}

// ==========================================
// CORE FUNCTIONS
// ==========================================

void setup() {
  // Initialize Serial communication at 9600 baud
  Serial.begin(9600);
  
  // Initialize I2C LCD
  lcd.init();
  
  // Turn on the LCD backlight
  lcd.backlight();
  
  // Calculate candidate name length once
  nameLength = strlen(CANDIDATE_NAME);
  
  // Initial telemetry read and display
  currentTemp = readLM35();
  updateNameRow();
  updateTemperatureRow();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Task 1: Name Scrolling (Fast loop for smooth visual transition if name > 16 chars)
  if (currentTime - lastScrollTime >= SCROLL_INTERVAL) {
    lastScrollTime = currentTime;
    updateNameRow();
  }
  
  // Task 2: Telemetry Loop (Every 2 seconds)
  // Reads temperature, updates LCD row 2, and transmits via Serial concurrently
  if (currentTime - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    lastTelemetryTime = currentTime;
    
    // Read temperature sensor
    currentTemp = readLM35();
    
    // Update display in real-time
    updateTemperatureRow();
    
    // Send reading to PC via USB Serial
    Serial.println(currentTemp, 1);
  }
}
