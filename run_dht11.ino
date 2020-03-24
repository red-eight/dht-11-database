#include <dht11.h>

const int dht11_pin = 4;
const int max_error_count = 10;

int invalid_checksum_count = 0;
int timeout_count = 0;

dht11 sensor;


void print_all_values();


void setup() {
  Serial.begin(9600);
  
  // When power is supplied to the DHT11, no instructions should be sent to the sensor for 1 second.
  delay(1000);
}


void loop() {  
  int ec = sensor.read(dht11_pin);
  if (ec == DHTLIB_OK) {
    invalid_checksum_count = 0;
    timeout_count = 0;
    print_all_values();
  }

  else if (ec == DHTLIB_ERROR_CHECKSUM) {
    ++invalid_checksum_count;
    if (invalid_checksum_count >= max_error_count) {
      invalid_checksum_count = 0;
      print_all_values();
      Serial.println("Checksum error.");
    }
  }

  else if (ec == DHTLIB_ERROR_TIMEOUT) {
    ++timeout_count;
    if (timeout_count > max_error_count) {
      timeout_count = 0;
      Serial.println("Timeout error.");  
    }
  }

  delay(2000);
}


void print_all_values() {
  Serial.print("Humidity (%): ");
  Serial.print(sensor.humidity_01);
  Serial.print(".");
  Serial.print(sensor.humidity_02);

  Serial.print(", Temperature (C): ");
  Serial.print(sensor.temperature_01);
  Serial.print(".");
  Serial.print(sensor.temperature_02);

  Serial.print(", Checksum: ");
  Serial.print(sensor.checksum);

  Serial.print(", Valid checksum: ");
  Serial.println(sensor.checksum_is_valid());
}
