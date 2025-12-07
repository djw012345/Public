# Public

```mermaid
flowchart TD

%% ===== 初始化流程 =====
A0["啟動程式"] --> A1["產生當日 Log 檔案"]
A1 --> A2["Serial 初始化 (/dev/ttyUSB0)"]
A2 --> A3["讀取 Latest.txt 還原 Map & Status"]
A3 --> A4["初始化黃燈狀態"]
A4 --> LOOP_START["主迴圈開始"]

%% ===== 主迴圈 =====
LOOP_START --> B1["等待 0.25 秒"]
B1 --> B2["counter++"]

B2 --> B3{"counter >= 600 ?"}
B3 -- "是" --> B4["寫入 Alive Log: Main Function is still ALIVE"]
B4 --> B5["counter = 0"]
B3 -- "否" --> B5

B5 --> B6{"Serial 是否有資料？"}
B6 -- "否" --> LOOP_START
B6 -- "是" --> C1["讀取 Arduino 20 bytes 狀態字串 (StatusTemp)"]

%% ===== 每個 slot 處理 =====
C1 --> D0["for i in 0..E_Rack_Shelf-1"]

D0 --> D1{"Status[i] 是否改變？"}
D1 -- "否" --> D0
D1 -- "是" --> D2{"Status[i] == '0' ? (Cassette 放入)"}

%% ===== Foup 放入流程 =====
D2 -- "是" --> IN1["寫入 Log: slot getting in"]
IN1 --> IN2["啟動 Timeout (3 秒)"]
IN2 --> IN3["清空鍵盤 buffer"]
IN3 --> IN4["ser.write(i) 觸發條碼讀取"]
IN4 --> IN5["等待條碼輸入 raw_input()"]

IN5 --> IN6{"Timeout? (超過 3 秒)"}
IN6 -- "是" --> T1["呼叫 interrupted()\n寫入 Timeout Log\n蜂鳴器兩聲"]
T1 --> D0
IN6 -- "否" --> IN7["條碼成功輸入\nBuzzer, Light"]
IN7 --> IN8["Map[i] = FoupID"]
IN8 --> IN9["寫入條碼 Log"]
IN9 --> IN10["printmap = 1"]
IN10 --> D0

%% ===== Foup 拿出流程 =====
D2 -- "否" --> OUT1["寫入 Log: slot taken"]
OUT1 --> OUT2["Map[i] = '0'"]
OUT2 --> OUT3["printmap = 1"]
OUT3 --> D0

%% ===== 更新畫面與檔案 =====
D0 --> E0{"printmap == 1 ?"}
E0 -- "否" --> LOOP_START
E0 -- "是" --> E1["清除畫面"]
E1 --> E2["將 Map 以 4x5 格列印"]
E2 --> E3["寫入 Map 至 Log 檔案"]
E3 --> E4["更新 Latest.txt"]
E4 --> E5["printmap = 0"]
E5 --> LOOP_START




```






```mermaid
flowchart TD
    A[物件放入] --> B[IR SENSOR 感測到物體]
    B --> C[啟動 Barcode Reader 3 秒]
    C --> D{是否讀取到 Barcode?}

    D -->|是| E[Web Service 上拋 Barcode 至 Server<br>三色燈閃一下綠光<br>蜂鳴器叫一聲]
    D -->|否| F[三色燈閃一下紅燈<br>蜂鳴器叫兩聲<br>需再次放入物件]
    
    F --> A


```


```mermaid

flowchart LR
    subgraph RPI_Block[Raspberry Pi 主控端]
        RPI[樹莓派<br/>負責資料接收、邏輯判斷、Web Service 上拋]
    end

    subgraph ARD_Block[Arduino Mega 感測器控制端]
        MEGA[Arduino Mega<br/>負責讀取 20 組 IR Sensor 與 Barcode Reader]
    end

    subgraph SENSOR_Block[感測器與讀取器]
        IR[20 組 IR Sensor]
        BR[Barcode Reader]
    end

    %% Connections
    IR --> MEGA
    BR --> MEGA
    MEGA -- USB / UART --> RPI


```




```txt
/*
  IR Sensor Health Check System
  自動檢測紅外線距離感測器健康狀態
  作者: ChatGPT x JIA_WEI Du
  功能:
  1. 檢查輸出電壓範圍
  2. 測試輸出是否隨距離變化
  3. 計算雜訊標準差
  4. 偵測長時間無變化
  5. 綜合健康評分輸出
*/

const int sensorPin = A0;      // 感測器接腳
const int sampleCount = 50;    // 每次取樣數
const float voltageMin = 0.3;  // 允許最小電壓
const float voltageMax = 3.0;  // 允許最大電壓
const unsigned long responseTimeout = 5000; // 無變化最長允許時間

float lastVoltage = 0;
unsigned long lastChangeTime = 0;

void setup() {
  Serial.begin(9600);
  delay(1000);
  Serial.println("=== IR Sensor Health Check System ===");
}

void loop() {
  // Step 1️⃣: 連續取樣
  float readings[sampleCount];
  for (int i = 0; i < sampleCount; i++) {
    readings[i] = analogRead(sensorPin) * (5.0 / 1023.0);
    delay(20);
  }

  // Step 2️⃣: 計算平均與標準差
  float mean = 0, stddev = 0;
  for (int i = 0; i < sampleCount; i++) mean += readings[i];
  mean /= sampleCount;
  for (int i = 0; i < sampleCount; i++) stddev += pow(readings[i] - mean, 2);
  stddev = sqrt(stddev / sampleCount);

  // Step 3️⃣: 電壓範圍檢查
  bool voltage_ok = (mean >= voltageMin && mean <= voltageMax);

  // Step 4️⃣: 反應變化檢查
  bool response_ok = abs(mean - lastVoltage) > 0.05; // 50mV 變化視為反應
  if (response_ok) {
    lastChangeTime = millis();
  }

  // Step 5️⃣: 超時檢測
  bool timeout_fault = (millis() - lastChangeTime > responseTimeout);

  // Step 6️⃣: 健康評分 (簡單線性估算)
  int health = 100;
  if (!voltage_ok) health -= 40;
  if (stddev > 0.15) health -= 25;
  if (!response_ok) health -= 15;
  if (timeout_fault) health -= 20;
  if (health < 0) health = 0;

  // Step 7️⃣: 輸出報告
  Serial.println("------------------------------------");
  Serial.print("平均電壓: "); Serial.print(mean, 2); Serial.println(" V");
  Serial.print("標準差: "); Serial.print(stddev, 3);
  Serial.println(" (雜訊程度)");
  Serial.print("健康評分: "); Serial.print(health); Serial.println(" / 100");

  if (!voltage_ok) Serial.println("⚠️ 電壓異常：可能供電問題或模組故障");
  if (stddev > 0.15) Serial.println("⚠️ 雜訊過高：可能鏡頭髒污或光線干擾");
  if (timeout_fault) Serial.println("⚠️ 無回應：感測器輸出卡死");
  if (health >= 90) Serial.println("✅ 狀態：健康正常");
  else if (health >= 70) Serial.println("⚠️ 狀態：需觀察");
  else Serial.println("❌ 狀態：建議更換感測器");

  Serial.println("------------------------------------\n");

  lastVoltage = mean;
  delay(2000);
}
```



