
#include <Wire.h>

#define MPU_ADDR 0x68

const unsigned long sampling_period_micros = 1000; 
unsigned long last_sample_time = 0;
bool python_pronto = false;
unsigned long last_pronto_time = 0;
const unsigned long pronto_interval = 500;

void writeRegister(uint8_t reg, uint8_t value){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission(true);
}

void configMPU(){
  writeRegister(0x6B, 0x00);
  delay(100);
  writeRegister(0x19, 0x00);
  writeRegister(0x1A, 0x01);
  writeRegister(0x1C, 0x10);
}

void readAccel(float &ax, float &ay, float &az){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  int16_t raw_x = (Wire.read() << 8) | Wire.read();
  int16_t raw_y = (Wire.read() << 8) | Wire.read();
  int16_t raw_z = (Wire.read() << 8) | Wire.read();

  ax = raw_x / 4096.0f;
  ay = raw_y / 4096.0f;
  az = raw_z / 4096.0f;
}

void setup(void) {
  Serial.begin(921600);
  Wire.begin();

  configMPU();
  delay(200);
}

void loop() {
  if (python_pronto) {
    unsigned long now = micros();

    if ((now - last_sample_time) >= sampling_period_micros) {
      last_sample_time = now; 

      float ax, ay, az;
      readAccel(ax, ay, az);

      Serial.write((uint8_t*) &ax, sizeof(ax));
      Serial.write((uint8_t*) &ay, sizeof(ay));
      Serial.write((uint8_t*) &az, sizeof(az));
    }

    if (Serial.available()){
      char cmd = Serial.read();
      if (cmd == 'C'){
        python_pronto = false;
        last_pronto_time = millis();
      }
    }
  }

  else{
    if(Serial.available()){
      char cmd = Serial.read();
      if (cmd == 'S'){
        python_pronto = true;
        last_sample_time = micros();
      }
    }

    if(millis() - last_pronto_time >= pronto_interval) {
      last_pronto_time = millis();
      Serial.println("PRONTO");
    }
  }
}