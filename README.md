# Public
```mermaind
flowchart TD
    A[Arduino MEGA] --> B[20 個 IR 感測器]
    A --> C[20 個條碼燈]
    A --> D[燈塔控制與蜂鳴器]
    B -->|感測狀態| E[讀取 IR 狀態]
    E --> F{狀態是否改變?}
    F -->|是| G[更新 Shelf_Status_temp]
    G --> H[透過 Serial 回傳 20 格狀態給 RPI]
    F -->|否| I[保持原狀]

    D -->|指令控制| J[Status1~Status4]
    J -->|倒數計時控制| K[LED / 蜂鳴器開關]
    
    C -->|條碼燈控制| L{RPI 送 Slot 編號}
    L -->|翻轉 BarcodeTimer| M[條碼燈開 / 關]

    H -->|樹莓派接收| N[RPI]
    M --> N
    K --> N

```


```mermaid
flowchart TD
    start[程式啟動] --> init_serial[初始化 Serial 與 Log]
    init_serial --> read_latest[讀取 Latest txt 還原 Map]
    read_latest --> init_status[初始化 Status 和 StatusTemp]
    init_status --> init_light[初始化堆疊燈 黃燈]
    init_light --> main_loop[進入主迴圈]

    main_loop --> check_serial{Serial 有資料嗎}
    check_serial -->|有| read_slot[讀取 Arduino 20 個 Slot 狀態]
    read_slot --> compare_status[比對 Status 與 StatusTemp]

    compare_status -->|Status 等於 0| cassette_in[Cassette 放入流程]
    compare_status -->|Status 等於 1| cassette_out[Cassette 拿出流程]

    cassette_in --> log_in[寫 Log slot getting in]
    log_in --> timeout[啟動 Timeout 3 秒]
    timeout --> wait_input[等待條碼輸入]
    wait_input -->|Timeout| timeout_action[Timeout 處理 寫入 N 與蜂鳴器]
    wait_input -->|輸入成功| save_map[儲存 FoupID 至 Map]
    save_map --> update_log[更新 Log 與 Latest txt]

    cassette_out --> log_out[寫 Log slot Taken]
    log_out --> clear_slot[清空 Map 對應 slot]
    clear_slot --> update_log

    update_log --> update_light[更新堆疊燈]
    update_light --> main_loop

    check_serial -->|無| main_loop


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



