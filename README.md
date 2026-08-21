# 임베디드 기기 대상 DOOM 포팅하기

본 저장소는 **임베디드 기기의 하드웨어 및 펌웨어를 분석하고, 분석한 실행 환경에 맞게 DOOM을 포팅하는 연구 프로젝트**의 수행 과정과 결과를 기록하기 위한 저장소입니다.

## Repository Notice

본 저장소의 모든 자료는 **프로젝트 수행, 연구 및 학습 목적**으로만 사용됩니다.

프로젝트 과정에서 다루는 펌웨어 분석, Firmware Modification, 디버깅 및 기타 보안 관련 기술은 **허가된 실습 장비와 연구 환경에서만 수행**하며, 타인의 시스템이나 기기에 대한 비인가 접근, 공격 또는 기타 악의적인 목적으로 사용하지 않습니다.

본 저장소의 내용은 실제 공격이나 불법 행위를 목적으로 하지 않으며, **임베디드 시스템의 구조와 동작 방식을 이해하고 분석하는 것을 목적으로 합니다.**

---

## Repository Structure

```text
.
├── main/
│   ├── images/
│   └── README.md
│
├── project/
│   ├── 1. Preliminary Research & Analysis/
│   │   ├── 1. Prior Research Analysis
│   │   │
│   │   ├── 2. Firmware Analysis/
│   │   │   ├── 1. Firmware & File System Analysis
│   │   │   └── 2. Boot Flow Analysis
│   │   │
│   │   └── 3. DOOM Porting Preparation/
│   │       ├── 1. Execution Environment Analysis
│   │       ├── 2. Web & SD Environment Analysis
│   │       ├── 3. DOOM Output Implementation
│   │       └── 4. Cross-Compilation & Pre-Testing
│   │
│   ├── 2. Physical Device Analysis/
│   │   ├── 1. Chip-Off & Firmware Extraction
│   │   ├── 2. Firmware Analysis
│   │   ├── 3. DOOM Porting
│   │   ├── 4. Firmware Modification
│   │   ├── 5. Rework
│   │   └── 6. Testing
│   │
│   └── README.md
│
└── README.md
```

---

## Directory

### [`main`](main/)

프로젝트 전체 내용을 정리하는 공간입니다.

연구의 필요성, 선행 연구, 연구 목표, 기술적 배경, 연구 설계 및 연구 대상 등 **프로젝트 전체에 대한 설명과 문서**를 정리합니다.

### [`project`](project/)

프로젝트의 실제 수행 과정을 단계별로 기록하는 공간입니다.

프로젝트는 크게 다음 두 단계로 구성됩니다.

1. **Preliminary Research & Analysis**  
   실제 기기 분석 전 수행하는 선행 연구, 펌웨어·파일 시스템 및 부팅 흐름 분석, DOOM 포팅 사전 준비 과정을 기록합니다.

2. **Physical Device Analysis**  
   실제 기기를 대상으로 수행하는 펌웨어 추출 및 검증, DOOM 포팅, 펌웨어 수정·리패키징, Rework 및 Testing 과정을 기록합니다.

---

## Project Flow

```text
Preliminary Research & Analysis
        ↓
Prior Research Analysis
        ↓
Firmware Analysis
        ↓
Firmware Structure Analysis
        ↓
File System Extraction
        ↓
File System & File Analysis
        ↓
Boot Flow Analysis
        ↓
DOOM Porting Preparation
        ↓
Execution Environment Analysis
        ↓
Web & SD Environment Analysis
        ↓
DOOM Output Implementation
        ↓
Cross-Compilation & Pre-Testing
        ↓
Physical Device Analysis
        ↓
Chip-Off & Firmware Extraction
        ↓
Firmware Verification & Difference Analysis
        ↓
DOOM Porting
        ↓
Firmware Modification & Repackaging
        ↓
Rework
        ↓
Testing
```
