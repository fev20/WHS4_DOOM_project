# 정적 구조 분석

이 프로젝트의 목표는 상용 IP 카메라에 DOOM을 포팅해 실제로 구동하는 것이다. 제조사가 의도하지 않은 외부 프로그램을 닫힌 임베디드 기기 위에서 끝까지 실행시킨다는 것은, 그 기기의 구조를 해독하고 동작을 제어할 수 있음을 보여주는 가장 직관적인 증거다.

외부에서 만든 프로그램을 이런 기기에 올려 실행하려면 세 가지 문제를 풀어야 한다.

1. 빌드 — 기기가 실제로 실행할 수 있는 바이너리를 만든다. 아키텍처·C 라이브러리·커널 ABI가 맞지 않으면 바이너리는 로드조차 되지 않거나 실행 중 죽는다.
2. 반입 — 그 바이너리를 기기 저장소에 올린다. 쓰기 가능한 위치와 충분한 공간, 그리고 전달 경로가 필요하다.
3. 실행 — 기기가 그 바이너리를 실제로 띄우게 한다. 부팅·초기화 흐름 중 끼어들 지점이 필요하다.

정적 분석은 기기를 구동하지 않고 펌웨어만으로 이 세 질문에 답하기 위한 작업이다. 실행 환경에서 비롯되는 변수 없이 기기의 구조를 먼저 확정해 두면, 이후의 크로스컴파일·반입·구동 시도가 근거 위에서 이루어진다. 각 질문에 어떤 분석이 대응하는지는 다음과 같다.

- 빌드: SoC·아키텍처·커널 버전·C 라이브러리·툴체인(1·4장), 링크 가능한 공유 라이브러리(6장)
- 반입: 쓰기 가능한 영역(6장), 삽입 가능한 여유 공간과 재조립 조건(2·7장), 전달 경로로서의 펌웨어 재조립(2·7장)·업데이트 기능(8장)·부팅 훅(5장)
- 실행: 부팅·초기화 체인과 자동 실행 삽입 지점(5장)

분석은 두 펌웨어에 걸쳐 진행되었다. `jooan.bin`은 실기기가 도착하기 전, 동일 기종 펌웨어를 내려받아 사전 분석한 것이고, `origin.bin`은 실기기를 열어 SPI 플래시에서 직접 덤프한 것이다. 두 펌웨어는 파티션 구조·부팅 체인·파일시스템 레이아웃이 동일했으므로 사전 분석 결과는 실기기에도 그대로 성립했고, 파티션 오프셋 등 핵심 값은 실기기 덤프로 교차검증하였다. 각 장에는 그 단계에서 실제로 사용한 명령어를 대상 파일 그대로 함께 실었다.

## 1. 분석 대상과 제원

DOOM을 크로스컴파일하려면 기기가 어떤 바이너리를 실행할 수 있는지부터 확정해야 한다. 아키텍처가 틀리면 바이너리가 로드되지 않고, C 라이브러리나 커널 ABI가 어긋나면 실행 중 죽기 때문이다. 아래 제원은 이 장에서 따로 뽑은 것이 아니라 2·3·4·6장의 분석에서 확인된 값을 한데 모은 요약으로, 각 행에 확인 출처를 함께 적는다.

| 항목 | 내용 | 빌드에서의 의미 | 확인 출처 |
|------|------|----------------|----------|
| 기기 | Jooan 계열 IP 카메라 | | 대상 기기 |
| SoC | Ingenic T23N | | 3장 `strings` → `Board info: T23N` |
| 아키텍처 | MIPS32r2, little-endian (mipsel) | 크로스컴파일 타깃 아키텍처 | 6장 `file jooanipc` |
| 커널 | Linux 3.10.14, `isvp_pike_1.0` | 사용 가능한 syscall·커널 기능 범위 | 4장 uImage 헤더·`strings` |
| C 라이브러리 | uClibc, `/lib/ld-uClibc.so.0` | glibc가 아니므로 uClibc에 맞춰 링크 | 6장 `file jooanipc` 인터프리터 |
| 툴체인 | gcc 5.4.0 Ingenic | 호환 바이너리 생성용 크로스컴파일러 | 4장 `strings` 빌드 문자열 |
| 플래시 | SPI NOR 8MB, 8,388,608 B | 반입 가능 총용량의 상한 | 2장 `ls -la`·`binwalk` |

전체 이미지는 SPI Flash를 그대로 덤프한 8MB 단일 바이너리이며, 내부는 여러 파티션으로 구성된 복합 이미지다.

## 2. 파티션 구조

펌웨어를 수정해 되돌려 넣으려면 각 영역이 어디서 시작해 얼마나 큰지를 바이트 단위로 알아야 한다. 파티션 맵은 이후 모든 수정·재조립의 좌표계이자, 어느 영역이 읽기 전용 squashfs이고 어느 영역이 쓰기 가능한 jffs2인지를 가르는 기준이기도 하다.

먼저 `file`로 형식을 확인했으나 알려진 포맷이 아니라 `data`로만 나왔고, `binwalk`로 내부 구성요소의 오프셋을 스캔한 뒤 `binwalk -e`로 추출하였다.

```bash
file jooan.bin
binwalk jooan.bin
binwalk -e jooan.bin
```

다만 `binwalk`는 매직바이트 패턴으로 시작점을 추측하는 도구라 무결성 검증을 하지 않으므로, 그 오프셋을 기기 스스로가 선언한 파티션 정보 `mtdparts`와 대조해 검증하였다. 커널 이미지에서는 `mtdparts=` 토큰만 나오고 실제 값이 없어, boot 파티션(첫 256KB)을 잘라 그 안의 `bootargs`에서 값을 확보하였다.

```bash
dd if=origin.bin of=uboot_test.bin bs=1 skip=0 count=262144
strings uboot_test.bin | grep -i "mtdparts\|bootargs"
```

여기서 얻은 `mtdparts=jz_sfc:256k(boot),32k(bootenv),...` 값의 크기를 누적해 계산한 오프셋을 `binwalk` 결과와 대조하니 kernel·rootfs·appfs·config 네 오프셋이 모두 일치하였다. 최종 파티션 맵은 다음과 같다.

| 파티션 | 시작 오프셋 | 크기 | 용도 |
|--------|------------|------|------|
| boot | 0x0 | 256k | U-Boot SPL과 본체 |
| bootenv | 0x40000 | 32k | bootcmd / bootargs |
| kernel | 0x48000 | 1472k | uImage, LZMA 압축 커널 |
| rootfs | 0x1B8000 | 2880k | squashfs, `/dev/mtdblock3` |
| appfs | 0x488000 | 3136k | squashfs, `/dev/mtdblock4` → `/mnt/mtd` |
| config | 0x798000 | 384k | jffs2, `/dev/mtdblock5` → `/opt` |
| confbak | 0x7F8000 | 32k | 설정 백업 |

추정값이 아니라 기기가 선언한 값을 기준으로 삼음으로써, 이후 커널 헤더·슈퍼블록 등을 바이트 단위로 잘라 볼 때의 오프셋 신뢰성을 확보하였다.

## 3. 부트로더 (U-Boot)

부트로더 분석은 커널이 어떻게 로드되는지와, 기기와 직접 소통할 통로가 있는지를 알려준다. 특히 시리얼 콘솔이 살아 있으면 부팅 로그 확인과 셸 접근의 통로가 되어, DOOM을 올린 뒤 구동 과정을 관찰·디버깅할 수단이 된다.

`strings`로 U-Boot 관련 문자열을 찾아 SPL과 본체의 존재를 확인하였다. `-t x`는 각 문자열의 오프셋을 함께 찍어 위치를 짚기 위함이다.

```bash
strings jooan.bin | grep -i "u-boot"
strings -t x jooan.bin | grep -i "u-boot"
```

`U-Boot SPL 2013.07-svn4700`과 본체 문자열이 확인되었고, SPL 영역인 0x2868 부근에는 PLL 클럭 설정·`sdram init start` 등 DRAM 초기화 문자열과 `Board info: T23N`이 함께 나왔다.

부팅 명령 `bootcmd`은 bootenv 파티션을 잘라 확인하였고, 커널 인자 `bootargs`는 2장에서 boot 파티션을 훑을 때 함께 확보한 것이다.

```bash
dd if=origin.bin bs=1 skip=262144 count=256 2>/dev/null | xxd   # bootenv → bootcmd
```

```
bootcmd=sf probe; sf read 0x80600000 0x48000 0x180000; bootm 0x80600000
bootargs=console=ttyS1,115200n8 ... init=/linuxrc rootfstype=squashfs root=/dev/mtdblock3 rw mtdparts=jz_sfc:...
```

`bootcmd`은 `sf probe`로 SPI Flash를 초기화한 뒤 `sf read`로 kernel 파티션(0x48000)을 DRAM(0x80600000)으로 복사하고 `bootm`으로 커널을 실행한다. 이 로드 오프셋 0x48000은 `binwalk`가 커널 uImage를 찾아낸 위치와 정확히 일치하였다. `bootargs`에서는 루트 파일시스템이 `/dev/mtdblock3`의 squashfs이고 첫 사용자 프로세스가 `/linuxrc`임을 확인하였다. 또한 `console=ttyS1,115200n8`로 시리얼 콘솔이 활성화되어 있어, UART를 통한 상호작용 가능성을 확인하였다.

## 4. 커널

커널 버전·빌드 정보는 DOOM 바이너리가 쓸 수 있는 커널 기능의 범위와 크로스컴파일 환경을 결정한다. 압축 방식과 uImage 포맷은 커널을 수정해 재조립해야 할 경우의 전제가 된다. kernel 파티션 선두 64바이트가 uImage 헤더이므로, 그 영역만 잘라 `xxd`로 필드를 읽었다.

```bash
dd if=jooan.bin bs=1 skip=$((0x48000)) count=64 2>/dev/null | xxd
```

| 필드 | 값 | 의미 |
|------|-----|------|
| Magic | `0x27051956` | U-Boot Legacy uImage |
| Data size | `0x162F0F`, 1,453,839 B | 압축 커널 payload |
| Load address | `0x80010000` | 압축 해제 후 배치 주소 |
| Entry point | `0x803782A0` | 커널 진입 주소 |
| OS / Arch | Linux / MIPS | |
| Type / Comp | Kernel / LZMA | 단일 압축 커널 |
| Image name | `Linux-3.10.14__isvp_pike_1.0__` | |

커널은 LZMA로 압축되어 있어, `binwalk -e`가 함께 풀어 둔 커널 파일(binwalk가 오프셋을 따 `48040`으로 이름 붙인다)에서 빌드 문자열을 확인하였다.

```bash
strings 48040 | grep -i "linux version"
```

빌드 문자열은 `Linux version 3.10.14__isvp_pike_1.0__ (root@ubuntu) (gcc 5.4.0 Ingenic ...) #1 PREEMPT Tue May 28 2024`로, 커널 버전·빌드 환경·컴파일러를 특정할 수 있었다. 이는 1장과 함께 크로스컴파일 환경을 확정하는 근거가 된다.

압축 해제는 수동으로도 교차검증했다. 헤더의 Data Size만큼 잘라 풀어 보았는데, `unlzma`는 종료마커(0xFF) 방식을 처리하지 못해 "Compressed data is corrupt"로 실패했고, 이 방식을 지원하는 파이썬 `lzma` 모듈로 해제해 같은 결과를 얻었다.

```bash
dd if=jooan.bin bs=1 skip=$((0x48000+64)) count=$((0x162f0f)) of=jooan_kernel.lzma
unlzma -k jooan_kernel.lzma    # 실패 → python lzma.decompress(data, format=lzma.FORMAT_ALONE)
```

Entry point·CRC·Timestamp는 버전 간 달라지는 필드로, 7장 버전 비교에서 다시 다룬다.

## 5. 부팅 체인

DOOM을 실행시키는 문제의 핵심이 이 장이다. 부팅 순서의 어느 지점에 끼어들면 외부 프로그램을 자동으로 띄울 수 있는지를 찾기 위해, 커널이 rootfs를 마운트한 뒤의 실행 순서를 최상위 진입점부터 추적하였다. 각 설정 파일을 순서대로 열어 따라갔다.

```bash
ls -la linuxrc              # → bin/busybox 심볼릭 링크
cat etc/inittab
cat etc/fstab
cat etc/init.d/rcS
cat startapp                # appfs 루트의 앱 진입점
```

`init=/linuxrc`의 `/linuxrc`는 심볼릭 링크로 최종적으로 `bin/busybox`를 가리켰다. 즉 PID 1은 busybox init이다. `inittab`과 `fstab`은 busybox 표준 템플릿을 거의 그대로 사용하였고, 벤더가 손댄 부분은 사실상 `::sysinit:/etc/init.d/rcS` 한 줄뿐이었다. 자동 실행 서비스의 실제 목록은 inittab이 아니라 rcS 안에 몰려 있다. busybox가 런레벨을 지원하지 않아 런레벨별 디렉토리 없이 rcS 하나에 초기화 로직을 집약한 구조다.

벤더가 작성한 `rcS`는 mdev 설정, 환경변수 설정, 네트워크 초기화, appfs와 config 마운트, Wi-Fi 칩 탐지·드라이버 삽입을 수행한 뒤 `goahead`·`system_call_daemon`을 백그라운드로 띄우고 마지막에 `/mnt/mtd/startapp`을 실행한다. 환경변수 단계에서 `PATH`에 `/mnt/mtd/run`, `LD_LIBRARY_PATH`에 `/mnt/mtd/lib`를 추가하는 것도 확인되었다. `startapp`은 `/opt` 여유공간 정리, DNS 설정, MAC 확정, `jzstart.sh`의 하드웨어 드라이버 로드를 거쳐 `goahead`·`my_watch_dog`·`syslogd`·`jooanipc` 등 핵심 데몬을 순차 기동한다.

```
Boot ROM → U-Boot(SPL → 본체) → Kernel(uImage) → rootfs 마운트
        → /linuxrc(busybox) → inittab → rcS → startapp → jooanipc(카메라 핵심 데몬)
```

실행 삽입 지점은 두 곳으로 확인되었다. 첫째, rcS와 startapp의 말미는 서비스를 순차 기동하는 구간이라, 여기에 한 줄을 더하면 외부 프로그램을 자동 실행시킬 수 있다. 둘째, startapp에는 `test -e /opt/etc/local.rc && source /opt/etc/local.rc` 구문이 있어, 쓰기 가능한 `/opt`의 `local.rc`가 부팅 시마다 실행되는 사용자 확장 지점으로 존재한다. 후자는 squashfs를 건드리거나 재플래싱하지 않고도 실행을 거는 경로가 된다.

## 6. 파일시스템 구성

이 장은 반입과 빌드 양쪽에 걸린다. 어디에 쓸 수 있는지와, DOOM이 동적으로 링크할 수 있는 라이브러리가 무엇인지를 확인하기 위함이다. 더불어 기기에 셸로 접근해 바이너리를 전달·실행할 수단이 있는지도 함께 본다.

rootfs는 busybox 기반의 범용 리눅스 골격이고, appfs는 벤더가 이 카메라 제품군을 위해 작성한 애플리케이션 계층으로 `/mnt/mtd`에 마운트된다. appfs에는 드라이버 로더 `jzstart.sh`, 앱 진입점 `startapp`, 공유 라이브러리와 `modules/*.ko` 커널 모듈이 담긴 `lib/`, 카메라 핵심 데몬 `jooanipc`와 `goahead`·`my_watch_dog` 등이 든 `run/`이 있다. `jooanipc`를 `file`로 확인하니 ELF 32-bit LSB MIPS, 동적 링크 `/lib/ld-uClibc.so.0`, stripped 바이너리였다. 기기가 uClibc 기반이므로 DOOM도 여기에 맞춰 링크해야 한다.

쓰기 가능 영역은 반입의 핵심 제약이다. 마운트 타입상 rootfs·appfs는 squashfs여서 읽기 전용이고, 런타임에 쓰기가 가능한 영역은 jffs2인 `/opt`와 tmpfs인 `/tmp`·`/run`뿐이다. 다만 tmpfs는 재부팅 시 소멸하므로, 한 번 띄워 보는 데는 `/tmp`로 충분하지만 영속적으로 올리려면 `/opt`나 펌웨어 재조립이 필요하다.

셸 접근 가능성은 로그인 보호가 걸려 있는가와 원격 셸 수단이 있는가를 shadow → rcS → telnetd 순서로 확인하였다.

```bash
file jooanipc
cat etc/shadow                  # root:$5$... → SHA-256 해시
cat etc/init.d/rcS              # telnetd 기동 구문 없음
find . -iname "telnetd*"        # /sbin/telnetd 바이너리는 존재
```

- 로그인 보호: `shadow`의 root 비밀번호가 `$5$...` 형식으로 SHA-256 해시가 적용되어 있다. 앞 숫자가 알고리즘을 가리키며 `$1$`은 MD5, `$6$`은 SHA-512다.
- 원격 셸: rcS에 telnetd 기동 구문이 없어 부팅 시 원격 셸이 자동으로 켜지지 않으나, `/sbin/telnetd` 바이너리 자체는 존재한다. 기능은 있으되 비활성 상태로, rcS에 한 줄만 추가하면 활성화되어 바이너리 전달·실행의 통로가 된다.
- goahead 이중 존재: rootfs의 `/bin/goahead`와 appfs의 `/mnt/mtd/run/goahead`에 각각 존재하며, startapp이 appfs판을 `/tmp`로 복사해 실행하므로 런타임 구동본은 appfs 버전이다.

## 7. 펌웨어 버전 비교

펌웨어를 수정해 반입하려면 DOOM과 리소스가 들어갈 여유 공간이 있는지, 그리고 수정한 이미지가 다시 마운트되려면 어떤 조건을 지켜야 하는지를 알아야 한다. 이를 확인하기 위해 구버전 `jooan.bin`과 신버전 `origin.bin`을 대조하였다. 두 이미지 모두 8MB로 전체 크기는 같아, 더 세밀한 단위로 들어갔다.

파티션 선두 96바이트가 squashfs 슈퍼블록이라 실제 사용량·빌드 시각을 담고 있으므로, 그 영역만 잘라 비교하였다.

```bash
ls -la jooan.bin realdump/origin.bin
dd if=jooan.bin           bs=1 skip=$((0x1B8000)) count=96 2>/dev/null | xxd   # rootfs
dd if=realdump/origin.bin bs=1 skip=$((0x1B8000)) count=96 2>/dev/null | xxd
dd if=jooan.bin           bs=1 skip=$((0x488000)) count=96 2>/dev/null | xxd   # appfs
```

| 항목 | 구버전 | 신버전 |
|------|--------|--------|
| rootfs 사용량 / inode | 2,438.2KB / 274 | 2,835.0KB / 284 |
| appfs 사용량 / inode | 3,122.9KB / 198 | 3,107.3KB / 203 |
| 빌드 시각 | 20241210 | 20260312 |

수치만으로는 어떤 파일이 바뀌었는지 알 수 없어, 파티션 전체를 블록 단위로 잘라 실제 파일 트리로 풀어 비교하였다.

```bash
dd if=realdump/origin.bin bs=1024 skip=$((0x1B8000/1024)) count=2880 of=origin_rootfs.squashfs
file *.squashfs
unsquashfs -d origin_rootfs_extracted origin_rootfs.squashfs
```

`file`이 읽은 사용량·inode·타임스탬프가 앞서 수동 파싱한 슈퍼블록 값과 일치해 오프셋 계산을 교차검증하였고, 파일 트리 비교에서는 신버전에 Wi-Fi 펌웨어·커널 모듈 등이 추가되어 파일이 10개 늘었으며 `goahead`·`rcS`·`shadow`가 변경되어 있었다.

반입 관점에서 중요한 두 수치를 얻었다. 첫째, 파티션 할당량 기준 신버전의 실제 여유 공간은 rootfs 45KB, appfs 28.7KB에 불과하다. 외부 프로그램을 펌웨어에 삽입할 때 반드시 이 크기 제약을 고려해야 한다. 둘째, `file`이 읽은 두 파일시스템 모두 압축 방식은 xz, 블록 크기 131072다. 수정한 이미지를 부트로더가 다시 마운트하게 하려면 재조립 시 이 압축 조건을 그대로 지켜야 한다.

## 8. 업데이트 로직

펌웨어를 직접 플래싱하는 것보다 안전한 반입 경로로 제조사의 정상 업데이트 기능을 쓸 수 있는지 확인하기 위함이다. 그러려면 업데이트가 어떻게 트리거되고 어떤 검증을 통과해야 하는지를 알아야 한다. 이름에 힌트가 있을 파일을 넓게 훑는 것부터 시작해, 핵심 바이너리 goahead의 문자열로 좁혀 들어갔다.

```bash
find origin_rootfs_extracted origin_appfs_extracted -type f \
  -iname "*upgrade*" -o -iname "*update*" -o -iname "*upload*" -o -iname "*firmware*"
cat origin_rootfs_extracted/etc/webs/apcam/adm/upload_firmware.asp
grep -rl "upload.bin" origin_rootfs_extracted origin_appfs_extracted 2>/dev/null | grep -v "bin/goahead"
strings origin_rootfs_extracted/bin/goahead | grep -iE "exec|system\(|sh -c|/bin/|/sbin/"
readelf -d origin_rootfs_extracted/bin/goahead | grep -i needed
```

웹 페이지 `upload_firmware.asp`의 업로드 폼은 요청을 `/cgi-bin/upload_app.cgi`로 보냈으나 그 CGI 파일은 존재하지 않았고, 업로드 저장 경로 `/tmp/upload.bin`을 참조하는 다른 프로세스도 없었다. goahead 바이너리에서 `execl`·`/bin/sh` 호출이 확인되어, 별도 데몬이 아니라 goahead가 업로드부터 후속 처리까지 직접 담당하는 구조임을 파악하였다.

검증·실행 흐름은 goahead 내부 문자열에서 확인하였다. 오프셋 주변을 넓게 보니 모델명(`cur_model`/`ori_model`, `Model is not same`), 버전(`Version inconsistency`), 무결성(`upgrade file CRC error!`, `md5=`), `QAUpgradeDecV1`, 그리고 `.rodata`의 `/tmp/upgrade/mnt/upgrade.sh`·`appfs upgrade success`가 순서대로 나타났다. 즉 모델명 → 버전 → 무결성 검증을 거쳐 최종 실행권이 업로드 이미지 안의 upgrade.sh로 넘어가는 파이프라인이 goahead 안에 존재한다. `readelf`의 NEEDED 목록에 없던 `QAUpgradeDecV1`은 심볼 테이블상 goahead 바이너리 자체(섹션 11, 오프셋 `0x43b2e4`, 664바이트)에 구현되어 있었다.

진입점별로 어떤 함수가 호출되는지를 함수 단위로 따라가는 일은 동적 분석을 통해 분석해야 할 것으로 보인다.

## 9. 종합 및 한계

정적 분석으로 DOOM 구동의 세 문제에 대한 밑그림을 기기 구동 없이 확보하였다. 빌드 측면에서는 타깃 아키텍처 mipsel, 커널 3.10.14, C 라이브러리 uClibc, 툴체인 gcc 5.4.0 Ingenic을 확정했다. 반입 측면에서는 쓰기 가능 영역 `/opt`·`/tmp`, 여유 공간 수십 KB, 재조립 조건 xz·131072, 그리고 세 가지 전달 경로인 펌웨어 재조립·업데이트 기능·`local.rc` 훅을 식별했다. 실행 측면에서는 rcS·startapp 말미와 `local.rc`라는 자동 실행 삽입 지점을 찾았다.

다만 문자열·심볼 수준 분석에는 한계가 있다. 업데이트 경로에서 어떤 요청이 어떤 조건에서 어떤 함수를 트리거하는지, `QAUpgradeDecV1`이 암호화 해제인지 단순 디코딩인지는 확정하지 못했다. 이들의 실제 동작과, 크로스컴파일한 DOOM이 이 환경에서 실제로 뜨는지는 디컴파일과 동적 분석을 통해 확정된다.
