# 임베디드 기기 대상 DOOM 포팅하기
> 연구 기간: 2026년 8월 ~ 2026년 10월 (약 3개월)

본 저장소는 WhiteHat School 4기에서 진행한 프로젝트로, **임베디드 기기의 하드웨어 및 펌웨어를 분석하고, 분석한 실행 환경에 맞게 DOOM을 포팅하는 연구 프로젝트**의 수행 과정과 결과를 기록하고 공유함으로써, 차후 진행될 임베디드 기기 관련 보안에 기여하고자 합니다.

---
```
Repository Notice

본 저장소의 모든 자료는 프로젝트 수행, 연구 및 학습 목적으로만 사용됩니다.

프로젝트 과정에서 다루는 펌웨어 분석, Firmware Modification, 디버깅 및 기타 보안 관련 기술은 허가된 실습 장비와 연구 환경에서만 수행하며, 타인의 시스템이나 기기에 대한 비인가 접근, 공격 또는 기타 악의적인 목적으로 사용하지 않습니다.

본 저장소의 내용은 실제 공격이나 불법 행위를 유도하는 목적으로 하지 않으며, 임베디드 시스템의 구조와 동작 방식을 이해하고 분석한 내용을 공유하는 것을 목적으로 합니다.
```

## 저자
> WhiteHat School 4기 Embediz 팀
- Mentor: 문석주
- PL: 장형범
- PM: 유수민
- Mentee: 김가온, 김규민, 김민서, 민준기, 손민우, 최수연, 황원민
  
---
## 초록 (Abstract)
### 필요성
### 목표
### 배경
### 대상
### 결과

## 키워드

## 프로젝트 목차
1. [Related Work](./Related%20Work)
    + [Analysis of Previous Research](./Related%20Work/Analysis%20of%20Previous%20Research/Readme.md)
2. [Target System and Analysis Environment](./Target%20System%20and%20Analysis%20Environment)
    + [Target System and Analysis Environment](./Target%20System%20and%20Analysis%20Environment/Target%20System%20and%20Analysis%20Environment/Readme.md)
3. [Firmware Analysis](./Firmware%20Analysis)
    + [Firmware Extraction](./Firmware%20Analysis/Firmware%20Extraction/Readme.md)
    + [Static Structure Analysis](./Firmware%20Analysis/Static%20Structure%20Analysis/Readme.md)
    + [Dynamic Structure Analysis](./Firmware%20Analysis/Dynamic%20Structure%20Analysis/Readme.md)
4. [Modification and Porting Environment Setup](./Modification%20and%20Porting%20Environment%20Setup/)
   + [Preliminary Practice in File Modification and Repackaging](./Modification%20and%20Porting%20Environment%20Setup/Preliminary%20Practice%20in%20File%20Modification%20and%20Repackaging/Readme.md)
   + [Cross-Compilation Environment Setup](./Modification%20and%20Porting%20Environment%20Setup/Cross-Compilation%20Environment%20Setup/Readme.md)
5. [DOOM Porting Implementation](./DOOM%20Porting%20Implementation/)
   + [Screen Output Implementation](./DOOM%20Porting%20Implementation/Screen%20Output%20Implementation/Readme.md)
   + [Control Input Implementation](./DOOM%20Porting%20Implementation/Control%20Input%20Implementation/Readme.md)
6. [Experiments and Results](./Experiments%20and%20Results/)
   + [Verification on the Actual Device](./Experiments%20and%20Results/Verification%20on%20the%20Actual%20Device/Readme.md)
   + [Results Analysis and Limitations](./Experiments%20and%20Results/Results%20Analysis%20and%20Limitations/Readme.md)
7. [Conclusion and Future Work](./Conclusion%20and%20Future%20Work/)
   + [References](./Conclusion%20and%20Future%20Work/References/Readme.md)
