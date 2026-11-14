#include <Wire.h>

#define ADXL_ADDR        0x53   // pino SDO em GND (com SDO em 3,3 V o endereço é 0x1D)

#define REG_DEVID        0x00
#define REG_BW_RATE      0x2C
#define REG_POWER_CTL    0x2D
#define REG_DATA_FORMAT  0x31
#define REG_DATAX0       0x32
#define REG_FIFO_CTL     0x38
#define REG_FIFO_STATUS  0x39

const uint8_t ODR_1600HZ   = 0x0E;   // taxa de saída de 1600 Hz (largura de banda de 800 Hz)
const uint8_t FORMATO_8G   = 0x0A;   // resolução total (D3) e faixa de ±8 g (D1:D0 = 10)
const uint8_t FIFO_BYPASS  = 0x00;
const uint8_t FIFO_STREAM  = 0x80;
const float   LSB_POR_G    = 256.0f; // sensibilidade em resolução total (~3,9 mg/LSB)

bool sensor_ok = false;
bool python_pronto = false;
unsigned long last_pronto_time = 0;
const unsigned long pronto_interval = 500;

void writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission(true);
}

uint8_t readRegister(uint8_t reg) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL_ADDR, 1, true);
  return Wire.read();
}

bool configADXL() {
  if (readRegister(REG_DEVID) != 0xE5) return false;  // identificação do ADXL345

  writeRegister(REG_POWER_CTL, 0x00);        // modo de espera durante a configuração
  writeRegister(REG_BW_RATE, ODR_1600HZ);
  writeRegister(REG_DATA_FORMAT, FORMATO_8G);
  writeRegister(REG_FIFO_CTL, FIFO_STREAM);
  writeRegister(REG_POWER_CTL, 0x08);        // inicia as medições
  return true;
}

void limparFifo() {
  writeRegister(REG_FIFO_CTL, FIFO_BYPASS);  // passar por bypass esvazia a FIFO
  writeRegister(REG_FIFO_CTL, FIFO_STREAM);
}

void readAccel(float *amostra) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(REG_DATAX0);
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL_ADDR, 6, true);

  // O ADXL345 envia primeiro o byte menos significativo de cada eixo
  uint8_t x0 = Wire.read();
  uint8_t x1 = Wire.read();
  uint8_t y0 = Wire.read();
  uint8_t y1 = Wire.read();
  uint8_t z0 = Wire.read();
  uint8_t z1 = Wire.read();

  int16_t raw_x = (int16_t)((x1 << 8) | x0);
  int16_t raw_y = (int16_t)((y1 << 8) | y0);
  int16_t raw_z = (int16_t)((z1 << 8) | z0);

  amostra[0] = raw_x / LSB_POR_G;
  amostra[1] = raw_y / LSB_POR_G;
  amostra[2] = raw_z / LSB_POR_G;
}

void setup() {
  Serial.begin(921600);
  Wire.begin();
  Wire.setClock(400000);   // I2C rápido (o ADXL345 suporta 400 kHz)
  delay(100);
  sensor_ok = configADXL();
}

void loop() {
  if (python_pronto) {
    uint8_t n = readRegister(REG_FIFO_STATUS) & 0x3F;  // amostras disponíveis na FIFO
    if (n > 32) n = 32;

    while (n > 0) {
      float amostra[3];
      readAccel(amostra);
      Serial.write((uint8_t*)amostra, sizeof(amostra)); // 12 bytes: x, y, z em g
      n--;
    }

    if (Serial.available()) {
      char cmd = Serial.read();
      if (cmd == 'C') {
        python_pronto = false;
        last_pronto_time = millis();
      }
    }
  }
  else {
    if (Serial.available()) {
      char cmd = Serial.read();
      if (cmd == 'S' && sensor_ok) {
        limparFifo();          // descarta amostras antigas antes de começar
        python_pronto = true;
      }
    }

    if (millis() - last_pronto_time >= pronto_interval) {
      last_pronto_time = millis();
      Serial.println(sensor_ok ? "PRONTO" : "ERRO_SENSOR");
    }
  }
}
