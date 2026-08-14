# 임베디드 기기 대상 DOOM 포팅하기

**Embedded System Analysis · Firmware Analysis · DOOM Porting**

홈캠의 하드웨어와 펌웨어를 분석하고,
분석한 실행 환경에 맞게 DOOM을 포팅하여 실제 기기에서의 구동을 목표로 한다.

<br>

[**Project Files →**](../project/)

---

## Contents

* [서론](#-서론)

  * [연구의 필요성](#연구의-필요성)
  * [선행 연구](#선행-연구)
  * [연구의 목표](#연구의-목표)
  * [기술적 배경](#기술적-배경)
* [연구 방법](#-연구-방법)

  * [연구 설계](#연구-설계)
  * [연구 대상](#연구-대상)
  * [연구 수행 절차](#연구-수행-절차)
* [결과](#-결과)
* [고찰](#-고찰)

<br>

---

# 01. 서론

## 연구의 필요성

임베디드 시스템의 구조와 동작 방식을 이해하기 위해서는 실제 기기를 직접 분석하는 과정이 필요하다.

임베디드 기기는 기기마다 하드웨어 구성과 펌웨어 환경이 달라, 이론만으로는 내부 구조와 프로그램 실행 과정을 정확하게 파악하기 어렵다.

이에 홈캠의 주요 부품과 펌웨어를 분석하고, 분석한 실행 환경에 맞게 DOOM을 포팅하여 외부 프로그램이 실제 장비에서 실행되는지 확인한다.

이를 통해 임베디드 기기의 **하드웨어 분석부터 펌웨어 분석과 실행 환경 검증까지의 전 과정**을 익히는 것을 목적으로 한다.

<br>

## 선행 연구

본 연구에서는 `IoT 기기 취약점 분석을 위한 펌웨어 추출 및 분석 환경 구축 방법론`을 선행 연구로 선정하였다.

해당 논문의 제3장 `IoT 기기 취약점 분석 환경 구축`에서 제시한 **Chip-Off, Firmware Extraction, Firmware Modify, Rework, Testing**의 방법과 절차를 본 연구에 반영한다.

본 연구에서는 선행 연구의 수행 절차를 기반으로 **Firmware Analysis에 중점을 두며**, Firmware Extraction 이후 추출한 펌웨어와 실행 환경을 분석한 뒤 **DOOM Porting**을 수행하고 Firmware Modify 단계로 진행한다.

<br>

## 연구의 목표

> **홈캠의 하드웨어 및 펌웨어 구조를 분석하고, 분석한 실행 환경에 맞게 DOOM을 포팅하여 실제 임베디드 기기에서 구동하는 것을 목표로 한다.**

<br>

## 기술적 배경

본 연구를 이해하고 수행하기 위해 필요한 임베디드 시스템 및 펌웨어 관련 기술적 개념을 정리한다.

<br>

---

# 02. 연구 방법

## 연구 설계

본 연구는 **사전 조사 및 분석**과 **실제 기기 연구**의 두 단계로 구성한다.

<p align="center">
  <img src="images/project1.png" alt="연구 설계" width="850">
</p>

<br>

## 연구 대상

> 연구에 사용되는 임베디드 기기의 하드웨어 구성, 펌웨어 및 실행 환경을 분석 대상으로 한다.

본 연구의 대상 기기는 중국 JOOAN사의 홈캠이다. 

<p align="center">
  <img src="images/jooan.png" alt="둠 포팅할 기기" width="850">
</p>
<br>

## 연구 수행 절차

전체 수행 자료는 아래 프로젝트 디렉터리에서 확인할 수 있다.

> **[Project Directory](../project/)**

### 1. Preliminary Research & Analysis

실제 기기를 분석하기 전 선행 연구와 펌웨어를 기반으로 분석 방법 및 수행 절차를 사전에 확인한다.

| Step | 수행 단계              |                                                                        Documentation                                                                        |
| :--: | ------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------: |
|  01  | 선행 연구 분석           |                     [Prior Research Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/1.%20Prior%20Research%20Analysis)                     |
|  02  | 펌웨어 구조 분석          |                 [Firmware Structure Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/2.%20Firmware%20Structure%20Analysis)                 |
|  03  | 파일 시스템 추출          |                      [File System Extraction](../project/1.%20Preliminary%20Research%20%26%20Analysis/3.%20File%20System%20Extraction)                      |
|  04  | 파일 및 파일 시스템 분석     |              [File & File System Analysis](../project/1.%20Preliminary%20Research%20%26%20Analysis/4.%20File%20%26%20File%20System%20Analysis)              |
|  05  | 파일 변조 및 리패키징 사전 실습 | [File Modification & Repackaging Practice](../project/1.%20Preliminary%20Research%20%26%20Analysis/5.%20File%20Modification%20%26%20Repackaging%20Practice) |

> **[Preliminary Research & Analysis →](../project/1.%20Preliminary%20Research%20%26%20Analysis/)**

<br>

### 2. Physical Device Analysis

사전 분석을 기반으로 실제 기기에서 펌웨어 추출부터 분석, DOOM Porting, 펌웨어 수정 및 검증까지 수행한다.

| Step | 수행 단계                          |                                                        Documentation                                                       |
| :--: | ------------------------------ | :------------------------------------------------------------------------------------------------------------------------: |
|  01  | Chip-Off 및 Firmware Extraction | [Chip-Off & Firmware Extraction](../project/2.%20Physical%20Device%20Analysis/1.%20Chip-Off%20%26%20Firmware%20Extraction) |
|  02  | Firmware Analysis              |                 [Firmware Analysis](../project/2.%20Physical%20Device%20Analysis/2.%20Firmware%20Analysis)                 |
|  03  | DOOM Porting                   |                      [DOOM Porting](../project/2.%20Physical%20Device%20Analysis/3.%20DOOM%20Porting)                      |
|  04  | Firmware Modification          |             [Firmware Modification](../project/2.%20Physical%20Device%20Analysis/4.%20Firmware%20Modification)             |
|  05  | Rework                         |                             [Rework](../project/2.%20Physical%20Device%20Analysis/5.%20Rework)                             |
|  06  | Testing                        |                            [Testing](../project/2.%20Physical%20Device%20Analysis/6.%20Testing)                            |

> **[Physical Device Analysis →](../project/2.%20Physical%20Device%20Analysis/)**

<br>

### 전체 수행 흐름

```text
Preliminary Research & Analysis
              │
              ▼
     Prior Research Analysis
              │
              ▼
   Firmware Structure Analysis
              │
              ▼
     File System Extraction
              │
              ▼
   File & File System Analysis
              │
              ▼
File Modification & Repackaging Practice
              │
              ▼
      Physical Device Analysis
              │
              ▼
  Chip-Off & Firmware Extraction
              │
              ▼
       Firmware Analysis
              │
              ▼
          DOOM Porting
              │
              ▼
     Firmware Modification
              │
              ▼
             Rework
              │
              ▼
            Testing
```

<br>

---

# 03. 결과



<br>

---

# 04. 고찰



<br>

---

<div align="center">

</div>
