# 임베디드 기기 대상 둠 포팅하기

## 서론
### 연구의 필요성
임베디드 시스템의 구조와 동작 방식을 이해하기 위해서는 실제 기기를 직접 분석하는 과정이 필요하다. <br>
임베디드 기기는 기기마다 하드웨어 구성과 펌웨어 환경이 달라, 이론만으로는 내부 구조와 프로그램 실행 과정을 정확하게 파악하기 어렵다.<br>
이에 홈캠의 주요 부품과 펌웨어를 분석하고, 분석한 실행 환경에 맞게 DOOM을 포팅하여 외부 프로그램이 실제 장비에서 실행되는지 확인한다.<br>
이를 통해 임베디드 기기의 하드웨어 분석부터 펌웨어 분석과 실행 환경 검증까지의 전 과정을 익힐 수 있다.<br>

### 선행 연구
본 연구에서는 `IoT 기기 취약점 분석을 위한 펌웨어 추출 및 분석 환경 구축 방법론`을 선행 연구로 선정하였다. <br>
해당 논문의 제 3장 `IoT 기기 취약점 분석 환경 구축`에서 제시한 Chip-Off, Firmware Extraction, Firmware Modify, Rework, Testing의 방법과 절차를 본 연구에 반영한다. <br>
본 연구에서는 선행 연구의 수행 절차를 기반으로 Firmware Analysis에 중점을 두며, Firmware Extraction 이후 추출한 펌웨어와 실행 환경을 분석한 뒤 DOOM을 포팅하고 Firmware Modify를 수행한다.

### 연구의 목표

### 기술적 배경

---
## 연구 방법
### 연구 설계
![구조](images/project1.png)

### 연구 대상


### 연구 수행 절차 [Project](../project) 
- 사전 조사 및 분석 [Preliminary Research & Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/)
  + 선행 연구 분석 [Prior Research Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/1.%20Prior%20Research%20Analysis)
  + 펌웨어 구조 분석 [Firmware Structure Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/2.%20Firmware%20Structure%20Analysis)
  + 파일 시스템 추출 [File System Extraction](../project/1.%20Preliminary%20Research%20%26%20Analysis/3.%20File%20System%20Extraction)
  + 파일 및 파일 시스템 분석 [File & File System Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/4.%20File%20%26%20File%20System%20Analysis)
  + 파일 변조 및 리패키징 사전 실습 [File Modification & Repackaging Practice](../project/1.%20Preliminary%20Research%20%26%20Analysis/5.%20File%20Modification%20%26%20Repackaging%20Practice)
- 실제 기기 연구 [Physical Device Analysis](../project/2.%20Physical%20Device%20Analysis)
  + Chip-Off 및 Firmware Extraction [Chip-Off & Firmware Extraction](../project/2.%20Physical%20Device%20Analysis/1.%20Chip-Off%20%26%20Firmware%20Extraction)
  + Firmware Analysis [Firmware Analysis](../project/2.%20Physical%20Device%20Analysis/2.%20Firmware%20Analysis)
  + DOOM Porting [DOOM Porting](../project/2.%20Physical%20Device%20Analysis/3.%20DOOM%20Porting)
  + Firmware Modification [Firmware Modification](../project/2.%20Physical%20Device%20Analysis/4.%20Firmware%20Modification)
  + Rework [Rework](../project/2.%20Physical%20Device%20Analysis/5.%20Rework)
  + Testing [Testing](../project/2.%20Physical%20Device%20Analysis/6.%20Testing)

---
## 결과


---
## 고찰

