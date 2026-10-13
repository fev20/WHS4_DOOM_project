# 동적 구조 분석

본 장에서는 추출한 펌웨어의 MIPS 바이너리를 QEMU에서 실행하고, 실제 카메라의 런타임 정보를 조사하여 정적 분석 결과를 검증한 과정을 설명합니다. 펌웨어나 보드 버전이 달라져도 같은 순서로 확인할 수 있도록 각 작업의 목적, 관찰 결과와 다음 판단의 근거를 함께 제시합니다.

동적 분석의 목적은 바이너리를 단순히 실행하는 데 있지 않습니다. 정적 분석에서 세운 가설에 실제 입력을 주고, 파일·네트워크·메모리 접근과 함수 실행을 관찰하여 어떤 실행 파일과 코드 경로가 실제로 사용되는지 확인하는 데 있습니다. 본 장은 분석 환경과 검증 방법까지만 다루며, 확인한 지점을 수정하거나 펌웨어에 반영하는 과정은 별도의 구현 문서에서 다룹니다.

동적 분석은 다음 방식으로 진행했습니다. 각 단계의 결과는 다음 단계에서 사용할 도구와 조사 대상을 결정하는 근거가 됩니다. 실행 결과가 정적 분석의 예상과 다르면 관련 함수와 실행 조건을 다시 검토한 뒤 재검증합니다.

```text
[1] 분석 대상·질문과 ELF 실행 조건 확인
          ↓
[2] BusyBox로 QEMU·GDB와 rootfs 검증
          ↓
[3] goahead의 rootfs·설정 영역 구성
          ↓
[4.1] HTTP 요청과 syscall 결과 연결
          ↓
[4.2] Ghidra로 오류 관련 함수·호출 관계 추정
          ↓
[4.3] GDB로 등록 함수의 인자·콜백 검증
          ↓
[5~6] 실기기의 /proc·dmesg로 교차검증
```

## 1. 분석 대상과 실행 조건 식별

같은 상품이라도 펌웨어 버전과 보드 리비전에 따라 CPU 정보, 실행 파일, 경로와 설정이 달라질 수 있습니다. 따라서 다른 버전에서 확인한 주소나 파일명을 그대로 사용하는 대신, 분석할 바이너리와 실행 조건을 먼저 식별해야 합니다.

주요 분석 대상으로는 웹 서비스를 담당하는 `goahead`를 선정했습니다. 이 프로세스는 외부 HTTP 요청을 받아 파일, 폼, 액션 등의 내부 처리기로 전달하므로 다음 질문을 동적 분석으로 확인할 수 있기 때문입니다.

- 어떤 `goahead` 복사본이 실제로 실행되고 어떤 라이브러리와 설정을 사용합니까?
- HTTP 요청을 보냈을 때 어떤 파일 접근과 오류가 발생합니까?
- Ghidra에서 확인한 요청 등록 함수와 콜백이 실행 중에도 실제로 등록됩니까?
- QEMU에서 확인한 결과 중 어떤 항목을 실기기에서 다시 검증해야 합니까?

### 1.1 바이너리 형식과 의존성 확인

바이너리 형식은 실행 파일이 어떤 CPU 명령어와 바이트 순서, ABI 및 로딩 방식을 사용하는지를 뜻합니다. 이 정보가 QEMU 종류와 GDB 아키텍처를 결정합니다. 예를 들어 MIPS little-endian ELF에는 `qemu-mipsel`을 사용하며, big-endian 바이너리에는 `qemu-mips`가 필요합니다.

여기서 의존성은 프로그램 실행에 필요한 공유 라이브러리만을 뜻하지 않습니다. 프로그램이 시작되고 기능을 수행하기 위해 참조하는 조건 전체를 의미하며, 다음 네 층으로 구분했습니다.

| 구분 | 확인 대상 | 확인하는 이유 |
|---|---|---|
| 실행 형식 | MIPS/MIPSEL, ELF32, ISA, ABI, endian | QEMU 종류와 GDB 아키텍처 결정 |
| 로더·라이브러리 | ELF interpreter, `DT_NEEDED`, uClibc, TLS 라이브러리 | 프로세스가 시작 가능한 실행 환경 구성 |
| 파일·설정 | `/etc/webs`, 인증서, `route.txt`, `/opt/conf/config.json` | 초기화와 요청 처리에 필요한 데이터 재현 |
| 런타임 환경 | 환경 변수, 실행 인자, 포트, 다른 daemon, 장치와 IPC | QEMU 재현 범위와 실기기 검증 범위 구분 |

```sh
file <binary>
readelf -h <binary>   # ISA, endian, ABI, ELF 유형 확인
readelf -A <binary>   # MIPS ABI와 ISA 확장 정보 확인
readelf -l <binary>   # 동적 로더와 메모리 segment 확인
readelf -d <binary>   # NEEDED 항목의 공유 라이브러리 확인
```

`readelf -l`의 `Requesting program interpreter`는 실행에 필요한 동적 로더의 경로를 보여주고, `readelf -d`의 `NEEDED` 항목은 실행 파일에 선언된 직접 공유 라이브러리를 보여줍니다. 추출한 rootfs에서 이 경로와 파일이 존재하는지, 심볼릭 링크가 올바른 대상을 가리키는지 확인합니다. 이 확인을 생략하면 아키텍처가 맞아도 로더 부재, 라이브러리 버전 차이 또는 잘못된 절대경로 때문에 실행이 중단될 수 있습니다.

분석한 `goahead`에서는 다음 결과를 확인했습니다.

| 항목 | 관찰 결과 | 분석 환경에 미친 영향 |
|---|---|---|
| 파일 형식 | ELF32, little-endian MIPS, 동적 링크, stripped | `qemu-mipsel-static`과 `gdb-multiarch` 선택 |
| ABI·ISA | O32 ABI, MIPS32r2 플래그 | GDB의 MIPS O32 호출 규약을 기준으로 인자 확인 |
| ELF 유형 | `EXEC`, 진입점 `0x004068c0` | 고정 주소형 실행 파일이므로 Ghidra와 GDB 주소를 직접 대조 가능 |
| 동적 로더 | `/lib/ld-uClibc.so.0` | rootfs 안에 로더와 링크 대상을 함께 보존 |
| 직접 의존 라이브러리 | `libpthread.so.0`, `libm.so.0`, `libmbedtls.so.13`, `libmbedx509.so.1`, `libmbedcrypto.so.6`, `libc.so.0`, `ld-uClibc.so.0` | 같은 펌웨어의 라이브러리 세트 사용 |

`readelf -d`는 실행 파일에 선언된 직접 의존성을 보여주지만, 실행 중에는 라이브러리의 간접 의존성도 적재될 수 있습니다. 실제 QEMU syscall 추적에서는 위 파일들과 함께 `libdl.so.0`도 열리는 것을 확인했습니다. 따라서 정적 의존성은 `readelf -d`로, 실행 중 실제 적재 파일은 `-strace`로 교차검증했습니다.

### 1.2 주요 용어와 런타임 경로

| 용어 | 의미 |
|---|---|
| PID | 실행 중인 프로세스마다 커널이 부여하는 번호입니다. 재부팅하거나 프로세스를 다시 시작하면 달라질 수 있습니다. |
| syscall | 사용자 프로그램이 파일, 메모리, 네트워크와 프로세스 관리 등의 커널 기능을 요청하는 공식 진입점입니다. 일반 함수 호출과 달리 사용자 공간에서 커널 공간으로 제어가 넘어갑니다. |
| `/proc` | 실행 중인 커널과 프로세스 정보를 파일 형태로 제공하는 가상 파일시스템입니다. 실제 플래시에 저장된 일반 파일은 아닙니다. |

바이너리, ELF, ISA와 ABI처럼 파일 자체의 형식을 설명하는 용어는 [Ghidra를 통한 정적 분석](../Ghidra를%20통한%20정적%20분석/README.md)에서 다룹니다. 이 장에서는 실행 중에만 확인할 수 있는 PID, syscall과 `/proc` 정보를 중심으로 설명합니다.

`/proc/<PID>` 아래에서 주로 확인하는 항목은 다음과 같습니다.

| 경로 | 확인할 수 있는 정보 |
|---|---|
| `exe` | 실행 파일을 가리키는 심볼릭 링크 |
| `cmdline` | 프로세스를 시작할 때 전달된 실행 파일명과 인자 |
| `environ` | 프로세스에 전달된 환경 변수 |
| `maps` | 실행 파일과 공유 라이브러리가 매핑된 메모리 주소 |

임베디드 Linux는 저장공간을 줄이기 위해 BusyBox의 제한된 명령만 제공하는 경우가 많습니다. PC Linux에서 사용하는 `readlink`, `tr`, `find` 등의 명령이 없거나 일부 옵션만 지원될 수 있습니다. 아래 명령은 가능한 예시이며, 지원되지 않으면 `ls -l /proc/<PID>/exe`, `cat`, BusyBox applet 또는 분석 PC로 복사한 파일을 이용합니다.

```sh
ps
ls -l /proc/<PID>/exe
tr '\0' ' ' < /proc/<PID>/cmdline
tr '\0' '\n' < /proc/<PID>/environ
cat /proc/<PID>/maps

cat /proc/cpuinfo
cat /proc/version
cat /proc/cmdline
cat /proc/mtd
cat /proc/mounts
df -h
```

PID, IP 주소와 파일 경로는 고정값이 아닙니다. 먼저 `ps`로 PID를 찾고 `/proc/<PID>/exe`가 가리키는 실제 실행 파일을 확인해야 합니다. 같은 이름의 실행 파일이 rootfs와 appfs처럼 여러 파티션에 존재할 수 있으므로, 실행 중인 파일과 각 후보의 `md5sum`을 비교하면 어느 복사본이 실행되었는지 판단할 수 있습니다. MD5는 여기서 파일 내용의 동일성만 비교하기 위한 값이며 보안상 무결성이나 진위를 보증하는 용도로 사용하지 않습니다.

## 2. QEMU 기반 분석 환경

### 2.1 BusyBox로 실행 환경 검증

대상 펌웨어는 MIPS little-endian 바이너리를 사용하므로 x86-64 PC에서 직접 실행할 수 없습니다. 실제 서비스보다 구조가 단순하고 실행 결과를 바로 확인할 수 있는 BusyBox를 먼저 실행하여 QEMU 선택, 동적 로더와 기본 라이브러리 경로가 맞는지 확인했습니다.

```bash
cd squashfs-root
qemu-mipsel-static -L ./ ./bin/busybox
```

`-L ./`은 ELF 인터프리터 경로의 prefix를 현재 rootfs로 지정합니다. 이에 따라 `/lib/ld-uClibc.so.0`과 해당 로더가 참조하는 라이브러리를 추출한 rootfs에서 찾습니다.

BusyBox는 여러 명령을 하나의 실행 파일에 포함하는 멀티콜 바이너리입니다. 다음 명령으로 해당 펌웨어의 BusyBox에 포함된 applet 목록을 확인할 수 있습니다.

```bash
qemu-mipsel-static -L ./ ./bin/busybox --list
```

`--list` 결과는 이후 분석에 사용할 수 있는 명령을 파악하는 참고 자료입니다. 특정 네트워크 기능의 존재 여부는 BusyBox applet뿐 아니라 독립 실행 파일, 심볼릭 링크, 실행 중인 프로세스와 포트도 함께 확인해야 합니다.

![QEMU에서 실행한 MIPS BusyBox](images/qemu-busybox.png)

BusyBox가 정상 실행되어 `qemu-mipsel-static`의 선택과 rootfs의 동적 로더·기본 C 라이브러리를 사용할 수 있음을 확인했습니다. 다만 이 결과가 `goahead`의 TLS 라이브러리, 설정 파일 또는 네트워크 초기화까지 보장하지는 않으므로, 다음 단계에서는 실제 분석 대상인 `goahead`를 같은 환경에서 실행했습니다.

### 2.2 syscall 추적으로 외부 동작 관찰

QEMU의 `-strace` 옵션으로 분석 대상 바이너리가 호출하는 syscall과 반환값을 확인했습니다. BusyBox에서는 추적 기능 자체가 동작하는지 확인하고, 이후 같은 옵션을 `goahead`에 적용하여 실제 서비스가 요구하는 파일과 네트워크 동작을 조사했습니다.

```bash
qemu-mipsel-static -strace -L ./ ./bin/busybox
```

![QEMU syscall 추적](images/qemu-strace.png)

`strace`가 보여주는 syscall은 프로그램 내부 함수보다 큰 단위의 동작을 파악하는 데 유용합니다. 실행 실패 직전의 syscall과 반환값을 보면 정적 분석에서 다시 찾아야 할 파일명, 오류 문자열과 기능 영역을 좁힐 수 있습니다. 예를 들어 다음과 같은 흐름을 확인할 수 있습니다.

- `open`·`stat`: 어떤 설정 파일과 웹 문서, 라이브러리를 찾는지 확인합니다.
- `mmap`: 실행 파일과 라이브러리가 메모리에 적재되는 과정을 확인합니다.
- `read`·`write`: 파일 또는 소켓을 통한 입출력과 오류 메시지를 확인합니다.
- `socket`·`bind`·`listen`·`accept`: 네트워크 서비스의 생성과 요청 수신 흐름을 확인합니다.
- 반환값: 파일 부재, 권한 문제, 잘못된 인자 등 실패 원인을 확인합니다.

분석 대상이 stripped 바이너리여도 syscall의 이름, 인자와 반환값은 심볼 제거 여부와 관계없이 관찰할 수 있습니다. 따라서 특정 요청 직후 어떤 파일을 열다가 실패했는지, 어느 포트에서 대기하는지와 같은 외부 동작을 먼저 찾고 이를 정적 분석의 단서로 사용할 수 있습니다. stripped ELF의 의미와 분석 방법은 [Ghidra를 통한 정적 분석](../Ghidra를%20통한%20정적%20분석/README.md)에서 설명합니다. 다만 `-strace`만으로 syscall 사이의 내부 함수 호출 관계까지 알 수 있는 것은 아닙니다.

QEMU의 `-strace`는 함수 호출 스택이 아니라 시스템 콜 추적 결과입니다.

또한 QEMU의 syscall 추적은 일부 syscall이나 플래그의 인자 해석이 불완전할 수 있으므로, 중요한 결과는 반환값·파일 경로·GDB 관찰 결과와 함께 교차검증합니다.

### 2.3 GDB 원격 디버깅

`gdb-multiarch`는 x86, ARM, MIPS 등 여러 ISA의 레지스터와 명령어를 해석할 수 있도록 구성된 GDB입니다. 분석 PC는 x86-64이지만 대상 바이너리는 MIPS이므로, 호스트용 기본 GDB 대신 MIPS 실행 상태를 해석할 수 있는 `gdb-multiarch`를 사용했습니다. QEMU를 원격 디버깅 대기 상태로 실행한 뒤 이에 연결했습니다.

```bash
# 터미널 1
qemu-mipsel-static -g 7777 -L ./ ./bin/busybox

# 터미널 2
gdb-multiarch ./bin/busybox
(gdb) target remote localhost:7777
(gdb) display/12i $pc
```

![GDB로 확인한 MIPS 명령어](images/qemu-gdb.png)

BusyBox의 `_start`와 초기 명령어를 확인했습니다. 이 결과는 QEMU remote stub 연결, MIPS little-endian 명령어와 레지스터 해석 및 진입점 중단이 가능하다는 환경 점검입니다. 프로그램 기능을 분석한 결과는 아닙니다. 실제 `goahead`의 등록 함수와 인자를 추적한 결과는 4.3절에서 설명합니다.

## 3. 실제 서비스 바이너리 실행

### 3.1 rootfs와 설정 영역 준비

실기기에서 `/`와 `/mnt/mtd`는 읽기 전용 SquashFS이지만 `/opt`는 읽기·쓰기가 가능한 JFFS2 config 파티션입니다. 제조사는 이 영역에 장치별 설정처럼 재부팅 후에도 유지되어야 하고 펌웨어 이미지와 별도로 변경되어야 하는 데이터를 저장합니다. 관찰한 펌웨어의 `goahead`는 `/opt/conf/config.json`을 참조하므로 rootfs만 추출한 환경에서는 필요한 설정이 없어 실행이 실패할 수 있습니다. `/etc/webs`, `route.txt`, `auth.txt` 등의 웹 문서와 라우팅·인증 설정도 함께 필요합니다.

바이너리 하나와 눈에 보이는 공유 라이브러리만 별도 디렉터리에 복사하면 절대경로로 참조하는 파일, 로더의 심볼릭 링크 또는 설정 영역이 빠지기 쉽습니다. SquashFS를 Linux 파일시스템에 추출하여 다음과 같은 원래 링크 구조를 보존했습니다.

```text
/bin/sh -> busybox
/lib/ld-uClibc.so.0 -> ld-uClibc-0.9.33.2.so
/lib/libc.so.0 -> libuClibc-0.9.33.2.so
```

`qemu-mipsel-static -L <rootfs>`의 `-L`은 주로 guest의 동적 로더와 라이브러리를 찾을 기준 경로를 제공합니다. 반면 `goahead`가 syscall로 `/etc/webs/route.txt`나 `/opt/conf/config.json` 같은 절대경로를 열면 단순한 `-L`만으로는 전체 파일시스템 구조를 재현하기 어렵습니다.

`chroot`는 추출한 rootfs를 프로그램의 `/`로 보이게 하므로 실행 파일, 라이브러리, 인증서, 웹 문서와 설정을 원래 절대경로에 둘 수 있습니다. 즉, `chroot`를 사용하는 이유는 보안을 위한 격리가 아니라 실기기와 같은 파일시스템 경로를 재현하고 수작업 복사에서 생기는 의존성 누락을 줄이기 위해서입니다.

초기 QEMU·GDB 분석에서는 보존한 rootfs를 `-L`의 기준 경로로 사용했습니다. 버전별 실행 비교에서는 rootfs 내부에 QEMU static 바이너리를 배치하고, 별도로 추출한 JFFS2 설정 영역을 rootfs 아래의 `/opt` 위치에 bind mount한 뒤 `chroot`를 사용하여 실제 절대경로를 재현했습니다. bind mount는 원본 디렉터리를 복사하지 않고 다른 경로에서도 같은 내용이 보이게 하는 Linux 기능입니다.

```bash
sudo cp "$(which qemu-mipsel-static)" squashfs-root/usr/bin/
sudo mount --bind jffs2-root squashfs-root/opt
sudo chroot squashfs-root /usr/bin/qemu-mipsel-static \
  /bin/goahead /etc/webs 0.0.0.0:18080
```

분석을 마치면 bind mount를 해제합니다.

```bash
sudo umount squashfs-root/opt
```

위 명령은 QEMU를 명시적으로 호출하는 방식입니다. 호스트에 MIPS용 binfmt가 등록된 환경에서는 `chroot` 안에서 `/bin/goahead`를 직접 실행할 수도 있습니다. 실행 인자는 대상 펌웨어에서 다시 확인합니다.

```sh
/bin/goahead /etc/webs 0.0.0.0:18080
```

포트는 기존 서비스와 충돌하지 않도록 분석 환경에 맞게 변경할 수 있습니다.

### 3.2 chroot 사용 시 안전 주의사항

`chroot`는 프로세스가 `/`로 인식하는 파일시스템 시작점만 변경합니다. 별도의 커널, 프로세스·네트워크·마운트 namespace 또는 가상 하드웨어를 만드는 기능이 아니며 보안 격리 수단으로 설계된 것도 아닙니다. 기본적으로 실행 사용자의 권한도 그대로 유지됩니다.

QEMU user-mode 역시 보드 전체를 가상화하지 않습니다. MIPS 명령어를 호스트 CPU에서 실행할 수 있도록 변환하고, 대상 프로그램의 syscall을 호스트의 대응 syscall로 변환하여 호스트 커널에 요청합니다. 따라서 `chroot`와 QEMU user-mode를 함께 사용해도 파일 경로 일부가 달라질 뿐, 프로그램은 여전히 호스트 커널과 자원을 사용합니다.

특히 `/proc`, `/sys`, `/dev` 또는 설정 디렉터리를 chroot 내부에 bind mount하면 해당 경로를 통해 호스트 상태와 장치가 노출될 수 있습니다. 같은 mount·network namespace에서 root 권한으로 실행한 명령은 호스트의 마운트나 네트워크 설정에 영향을 줄 수 있습니다. 펌웨어의 `rcS`, `startapp` 같은 초기화 스크립트를 통째로 실행할 때 다음 명령을 주의해야 합니다.

- `reboot`, `poweroff`, `killall`
- `mount`, `umount`
- `ifconfig`, `route` 등의 네트워크 변경
- `devmem` 및 장치 노드 접근

안전한 분석을 위해 다음 원칙을 적용합니다.

1. `rcS`, `startapp`과 이들이 호출하는 하위 스크립트를 텍스트로 먼저 검토합니다.
2. 전체 부팅 스크립트를 실행하지 않고 필요한 환경 변수, 파일과 디렉터리만 준비한 뒤 대상 바이너리를 개별 실행합니다.
3. `/proc`, `/sys`, `/dev`는 필요성을 확인하기 전까지 bind mount하지 않습니다. 필요한 경우에도 가능한 범위에서 읽기 전용으로 제한합니다.
4. root 권한은 chroot 구성과 mount에 필요한 구간으로 제한하고, 대상 프로그램은 가능하면 권한을 낮춰 실행합니다.
5. 네트워크와 장치 접근이 필요한 실험은 스냅샷으로 복구할 수 있는 별도의 가상 머신이나 격리된 실행 환경에서 수행합니다.
6. 무한 대기와 반복 실행에 대비해 `timeout`을 사용하고, 종료 후 bind mount가 해제되었는지 확인합니다.

관련 동작은 [QEMU User space emulator 공식 문서](https://www.qemu.org/docs/master/user/main.html)와 [GNU Coreutils의 chroot 설명](https://www.gnu.org/software/coreutils/manual/html_node/chroot-invocation.html)에서 확인할 수 있습니다.

## 4. 실행 결과를 정적 분석과 연결하기

### 4.1 입력 기반 syscall 분석

`strace`는 내부 함수 이름을 직접 보여주지는 않지만, 프로그램이 외부에 요청한 파일·소켓 동작과 반환값을 보여줍니다. 따라서 HTTP 요청과 syscall의 변화를 연결하면 Ghidra에서 다시 조사할 문자열과 기능 영역을 좁힐 수 있습니다.

권한에 따른 포트 차이를 배제하기 위해 18080 포트를 사용하고, 준비한 rootfs로 chroot한 상태에서 다음과 같이 로그를 수집했습니다.

```bash
/usr/bin/qemu-mipsel-static -strace \
  /bin/goahead /etc/webs 0.0.0.0:18080 > goahead.log 2>&1
```

서버가 18080 포트에서 대기하는 것을 확인한 뒤 다른 터미널에서 다음과 같이 정적 페이지를 요청합니다.

```bash
curl -v http://127.0.0.1:18080/home.htm
```

정상 실행 로그에서는 다음 흐름을 확인했습니다. 전체 raw trace를 나열하지 않고 환경 구성과 요청 처리의 성공을 판별할 수 있는 syscall만 발췌했습니다.

```text
open("/lib/libpthread.so.0", O_RDONLY) = 3
open("/lib/libmbedtls.so.13", O_RDONLY) = 3
open("/etc/webs/route.txt", O_RDONLY) = 3
open("/etc/webs/auth.txt", O_RDONLY) = 3
bind(... 0.0.0.0:18080 ...) = 0
listen(3, 128) = 0
open("/opt/conf/config.json", O_RDONLY) = 4
accept(3, ...) = 5
stat64("/etc/webs/home.htm", ...) = 0
open("/etc/webs/home.htm", O_RDONLY) = 7
```

이 결과는 로더와 라이브러리가 적재되고, 웹 및 장치 설정을 읽은 뒤 18080 포트에서 요청을 수신하여 실제 문서 파일을 열었다는 의미입니다. 즉, 프로세스가 종료되지 않았다는 사실만이 아니라 설정 초기화부터 HTTP 파일 응답까지의 실행 조건이 갖춰졌음을 보여주는 성공 기준입니다.

### 4.2 버전별 syscall 차이로 초기화 문제 식별

동일한 QEMU·chroot 환경에서 구버전 `goahead`는 웹 문서를 제공했지만 실기기에서 추출한 다른 버전은 같은 요청을 정상 처리하지 못했고, 파일 해시도 달라 서로 다른 빌드임을 확인했습니다. 이에 환경 조건을 고정한 상태에서 두 바이너리의 초기화 과정에 어떤 차이가 있는지 조사했습니다.

동일한 실행 인자와 포트로 수집한 로그의 핵심 차이는 다음과 같습니다.

```text
# 정상 버전
stat64("/etc/webs/home.htm", ...) = 0
open("/etc/webs/home.htm", O_RDONLY) = 7

# 오류 버전
Assertion 0 <= sd && sd < symMax, failed at runtime.c 1978
stat64("null/", ...) = -1 ENOENT
open("null/", O_RDONLY) = -1 ENOENT
```

오류 버전도 `bind`, `listen`, `accept`에는 성공했으므로 네트워크 초기화 전체가 실패한 것은 아닙니다. 차이는 요청받은 문서를 찾는 단계에서 나타났으며, `null/`은 문서 루트가 정상적으로 설정되지 않았다는 가설로 이어졌습니다. 이 가설을 설명할 수 있는 함수를 Ghidra에서 다음 기준으로 선별했습니다.

| 조사 함수 | 선정 근거 |
|---|---|
| `websSetDocuments` | syscall에서 문서 루트가 `null`로 사용되었으므로 문서 루트를 저장하는 함수와 XRef 조사 |
| `websOpenAuth` | `auth.txt` 처리 구간의 assertion과 버전별 `websOpen` 호출 차이를 설명하는 인증 초기화 경로 조사 |
| `hashCreate` | `sd`, `symMax` assertion과 관련된 내부 심볼·해시 테이블의 생성 여부 조사 |
| `websFileHandler` 계열 | 요청 URI가 실제 문서 경로로 조합되는 지점 조사 |

두 버전의 `websOpen` 호출 관계를 비교한 결과 `websSetDocuments`와 `websOpenAuth`의 초기화 차이를 확인했습니다. 이로써 조사 범위를 설정 파일 전체나 QEMU 환경이 아니라 문서 루트와 인증 초기화 코드로 좁힐 수 있었습니다. 후속 검증에서는 `route.txt`의 catch-all route에 `dir=/etc/webs`를 명시했을 때 `/etc/webs/home.htm` 접근이 정상화되는 것을 확인했습니다. 구체적인 설정 변경 과정과 결과는 [goahead 웹루트 수정](../../파일%20변조%20및%20리패키징%20사전%20실습/goahead/README.md)에서 설명합니다.

```text
동일 조건에서 두 버전 실행
        ↓
정상 경로와 null 경로의 syscall 차이 확인
        ↓
문서 루트 경로 설정 함수가 호출되지 않았다는 가설 수립
        ↓
Ghidra에서 관련 함수와 버전별 호출 관계 비교
        ↓
후속 단계의 수정 지점과 재검증 기준 결정
```

### 4.3 등록 함수로 외부 입력과 콜백 후보 연결

초기화 오류와 별도로 외부 HTTP 입력과 관련된 내부 함수를 선별하기 위해 요청 등록 구조를 조사했습니다. 바이너리에 남아 있는 GoAhead 관련 심볼을 확인한 뒤, 공식 API의 역할과 호출 관계를 기준으로 등록 함수를 분석 대상으로 선택했습니다.

- `websDefineHandler`는 HTTP 요청 처리기를 등록하므로 URI 처리 방식과 service 함수를 연결하는 경계입니다.
- `websDefineAction`은 이름과 C 콜백을 연결하여 `/action/NAME` 요청을 처리합니다.
- 분석한 바이너리의 `websFormDefine`은 form 이름과 장치별 콜백 주소를 연결합니다.
- `formDefineIPcamAPI`에는 다수의 `websFormDefine` 호출이 모여 있으므로 제조사 API를 한 번에 조사할 수 있습니다.

GoAhead의 handler 및 action 구조는 [Request Handler 공식 문서](https://www.embedthis.com/goahead/doc/developers/handlers.html)와 [GoActions 공식 문서](https://www.embedthis.com/goahead/doc/users/goactions.html)에서도 확인할 수 있습니다. `websFormDefine`의 구체적인 인자 관계는 이 바이너리의 Ghidra 호출부와 GDB 실행 결과로 확인했습니다.

Ghidra에서는 다음 관계를 가설로 세웠습니다.

```text
websOpen
  ├─ formDefineIPcamAPI
  │    └─ websFormDefine(name, callback)
  └─ 각 기능 초기화 함수
       └─ websDefineHandler(name, service, close, ...)
```

앞 절에서 구성한 chroot 환경에서 `goahead`를 QEMU의 GDB 대기 상태로 실행하고, 다른 터미널에서 동일한 바이너리를 지정한 `gdb-multiarch`로 연결할 수 있습니다. 아래 명령의 rootfs 경로와 포트는 분석 환경에 맞게 변경합니다.

```bash
# 터미널 1
sudo chroot squashfs-root /usr/bin/qemu-mipsel-static \
  -g 7777 /bin/goahead /etc/webs 0.0.0.0:18080

# 터미널 2
gdb-multiarch squashfs-root/bin/goahead
(gdb) target remote localhost:7777
```

QEMU-GDB에서 동일한 함수에 중단점을 설정하고 MIPS O32 호출 규약에 따라 `$a0`~`$a3`를 관찰했습니다.

```gdb
break *<websFormDefine의 실행 주소>
continue
x/s $a0
p/x $a1
bt
```

정적 분석과 동적 검증의 대응 결과는 다음과 같습니다.

| 정적 분석 가설 | GDB 검증 방법 | 실제 관찰 |
|---|---|---|
| `formDefineIPcamAPI`가 장치 form을 등록함 | `websFormDefine` 중단점에서 backtrace 확인 | 호출자가 `formDefineIPcamAPI`임을 확인 |
| `websFormDefine`의 첫 인자가 form 이름임 | `x/s $a0` | `reboot`, `upgradeFW`, `version`, `getDeviceInfo` 등 확인 |
| 두 번째 인자가 callback 주소임 | `p/x $a1` | 이름별로 서로 다른 함수 주소 확인 |
| `websDefineHandler`가 요청 handler를 등록함 | 이름과 service 인자 및 backtrace 확인 | `/cgi-bin-0`, `/goform-0`, `action`, `file`, `upload`, `jst` 등 확인 |

대표적인 form 등록 결과는 다음과 같습니다.

| form 이름 | callback 주소 |
|---|---:|
| `version` | `0x0040f7d4` |
| `reboot` | `0x0040f8f8` |
| `upgradeFW` | `0x0040fb98` |
| `RebootDev` | `0x0040f990` |
| `getDeviceInfo` | `0x00410f5c` |

주소는 분석한 펌웨어에서의 관찰값입니다. 다른 버전에서는 이름 문자열, 심볼과 XRef로 등록 함수를 다시 찾고 해당 바이너리의 주소로 중단점을 설정해야 합니다. 이 분석으로 수백 개의 내부 함수 중 외부 입력과 관련된 후보를 우선순위화할 수 있었습니다. `version`과 같은 조회 기능은 요청 전달 경로를 확인할 후보이고, `upgradeFW`, `reboot`처럼 상태를 변경하는 기능은 먼저 정적 분석하고 통제된 환경에서만 다뤄야 하는 후보입니다.

다만 시작 시 이름과 콜백이 등록되는 것을 관찰한 사실만으로 `/goform/version`과 같은 특정 URL이 실제 콜백에 도달한다고 단정할 수는 없습니다. 라우팅과 인증을 포함한 종단 간 관계를 입증하려면 해당 콜백에 중단점을 설정하고 실제 HTTP 요청을 보낸 뒤 중단점 도달과 응답을 함께 확인해야 합니다. 현재 확인한 범위는 등록 관계까지이며, 모든 form의 종단 간 요청 검증을 완료한 것은 아닙니다.

### 4.4 Ghidra 주소와 실행 주소 대응

PIE(Position Independent Executable)는 특정 기준 주소에 고정되지 않고 다른 주소에 적재되어도 실행할 수 있도록 만든 위치 독립 실행 파일입니다. 주소 공간 배치 난수화가 적용된 환경에서는 실행할 때마다 적재 기준 주소가 달라질 수 있으므로, Ghidra에 표시된 정적 주소와 실제 실행 주소가 다를 수 있습니다.

분석한 `goahead`는 `readelf`에서 `EXEC`, 진입점 `0x004068c0`으로 확인된 고정 주소형 실행 파일입니다. GDB의 `info files`에서도 같은 진입점과 `.text`, `.rodata`, `.data` 영역을 확인했으므로, 본체 함수는 Ghidra 주소와 같은 주소에 중단점을 설정할 수 있었습니다.

반면 PIE 실행 파일이나 공유 라이브러리는 실행 시 기준 주소를 반영해야 합니다. 실제 함수 주소는 다음 관계로 계산합니다.

```text
실행 주소 = Ghidra의 정적 주소
          + (실행 시 모듈 기준 주소 - ELF의 원래 기준 주소)
```

괄호 안의 차이를 load bias라고 합니다. QEMU의 GDB stub에 연결한 뒤 `info files`로 주 실행 파일의 guest 주소를 확인하고, 공유 라이브러리는 `info sharedlibrary`와 guest 매핑을 이용합니다. GDB가 라이브러리 파일을 해석할 수 있도록 다음과 같이 rootfs의 로컬 복사본을 지정할 수 있습니다.

```gdb
set sysroot <rootfs>
set solib-search-path <rootfs>/lib
info files
info sharedlibrary
```

## 5. 실기기 접근과 런타임 조사

### 5.1 접근 경로 선택

UART 접근을 검토했으나 USB 직렬 변환기 측 신호가 5V이고 대상 보드는 3.3V로 판단되어, 레벨 시프터 없이 직접 연결하지 않았습니다. 대신 허가된 실습 기기의 Wi-Fi AP에 연결하고 TCP 1111의 Telnet 셸을 이용했습니다.

커널 로그에는 UART1이 `ttyS1`으로 등록되어 있었지만, 부팅 인자에는 `console=null`이 지정되어 있고 초기 콘솔을 열지 못했다는 메시지도 기록되어 있었습니다. 따라서 UART 장치의 존재만으로 부팅 콘솔을 사용할 수 있다고 판단할 수 없습니다.

```powershell
Test-NetConnection 10.68.68.22 -Port 1111
```

![Telnet 포트 확인](images/telnet-port.png)

![실기기 root 셸](images/telnet-shell.png)

실험 당시 `id` 결과는 `uid=0(root) gid=0(root)`였습니다. IP 주소와 포트는 펌웨어 설정에 따라 달라질 수 있으므로 고정값으로 가정하지 않습니다.

### 5.2 프로세스와 부팅 상태

![실기기 프로세스 목록](images/process-list.png)

관찰한 주요 프로세스는 다음과 같습니다.

| 프로세스 | 확인한 역할 |
|---|---|
| `{linuxrc} init` | PID 1, BusyBox 기반 초기화 |
| `telnetd -p 1111 -l /bin/sh` | 분석용 셸 제공 |
| `goahead` | 웹 서비스 |
| `my_watch_dog` | 주요 서비스 감시 |
| `jooanipc` | 카메라 핵심 애플리케이션 |
| `udhcpd`, `hostapd` | Wi-Fi AP와 DHCP 제공 |

프로세스 번호는 부팅할 때마다 달라질 수 있으므로 이름으로 PID를 찾은 뒤 `/proc`를 조회합니다.

```sh
cat /proc/cmdline
cat /proc/mtd
cat /proc/mounts
cat /proc/modules
```

![실기기 부팅 인자와 시스템 정보](images/runtime-system-info.png)

| 위치 | 형식 | 상태 | 포팅 관점의 의미 |
|---|---|---|---|
| `/` | SquashFS | 읽기 전용 | 변경하려면 리패키징 필요 |
| `/mnt/mtd` | SquashFS | 읽기 전용 | appfs 실행 파일·라이브러리 위치 |
| `/opt` | JFFS2 | 읽기·쓰기, 여유 약 244~268KB | 소규모 설정 저장에 적합 |
| `/tmp` | tmpfs | 읽기·쓰기, 여유 약 18.5MB | 임시 파일용이며 재부팅 시 소멸 |
| `/tmp/sd` | VFAT SD 카드의 수동 마운트 지점 | 읽기·쓰기, 여유 약 557MB | 분석 과정에서 쓰기 가능 여부를 확인하기 위해 사용 |
| `/mnt/sd_card` | 제조사 애플리케이션이 사용하는 SD 경로 | 마운트된 경우 읽기·쓰기 | 실제 운용 경로로 사용 |

### 5.3 커널 로그와 장치 초기화

`dmesg`와 `/proc/devices`, `/proc/interrupts`, `/proc/iomem`을 함께 확인하여 커널이 인식한 하드웨어와 실제 활동 상태를 조사했습니다.

```sh
dmesg
cat /proc/devices
cat /proc/interrupts
cat /proc/iomem
```

| 확인 항목 | 관찰 결과 |
|---|---|
| CPU 및 클럭 | Ingenic XBurst, CPU 클럭 1,400MHz |
| 메모리 | 커널 인자에서 43,548KB 지정, 초기화 후 약 38,136KB 사용 가능 |
| 플래시 | XM25QH64C SPI NOR와 7개 MTD 파티션 등록 |
| SD 인터페이스 | MMC block major 179 및 `jzmmc_v1.2` 드라이버 등록 |
| 영상 장치 | IPU, ISP, IVDC와 Helix 관련 영역 및 인터럽트 확인 |
| 네트워크 | USB Wi-Fi 드라이버 초기화, 유선 GMAC probe 실패 |
| 카메라 센서 | 주 센서 `sc2337p` 탐지 및 스트림 활성화 |
| 입력·기타 장치 | `gpio-keys`, watchdog, 오디오와 모터 드라이버 등록 |

`/proc/interrupts`에서 IPU, ISP, I2C와 USB 등의 누적 카운트가 0이 아닌 것을 확인했습니다. 이는 부팅 이후 해당 인터럽트가 적어도 한 번 이상 발생했음을 보여줍니다. 반면 후보 보조 센서의 I2C 탐색 실패처럼 초기화 중 예상 가능한 오류도 있으므로, `dmesg`의 오류 문자열만으로 장치 고장을 단정하지 않습니다.

이 장치들은 호스트 커널을 사용하는 QEMU user-mode에서 재현되지 않습니다. 따라서 사용자 공간 바이너리의 실행과 파일 접근은 QEMU에서 조사하고, 장치 드라이버와 하드웨어 동작은 실기기 로그로 확인했습니다.

### 5.4 CPU와 메모리

| 항목 | 실기기 관찰값 |
|---|---|
| SoC 계열 | Pike / Ingenic XBurst |
| CPU | 단일 코어, BogoMIPS 1386.49 |
| `/proc/cpuinfo` ISA | `mips32r1` |
| 커널 | Linux 3.10.14 `isvp_pike` |
| 빌드 컴파일러 | Ingenic gcc 5.4.0 |
| 전체 RAM | 38,324KB |
| 측정 당시 여유 RAM | 13,064KB |
| Swap | 없음 |

`/proc/cpuinfo`는 `mips32r1`을 보고했지만 분석한 ELF에는 MIPS32r2 플래그가 존재했습니다. CPU 정보는 하드웨어 관찰값, ELF 플래그는 해당 프로그램의 빌드 조건이므로 각각 기록하고 QEMU와 실기기에서 실제 호환성을 검증했습니다.

### 5.5 실행 중인 `goahead` 확인

```sh
ls -l /proc/129/exe
cat /proc/129/cmdline
cat /proc/129/environ
cat /proc/129/maps
md5sum /proc/129/exe
```

![goahead 환경 변수](images/goahead-environ.png)

![goahead 메모리 매핑](images/goahead-maps.png)

대상 장비에는 `readlink` 명령이 없어 `ls -l /proc/129/exe`로 심볼릭 링크의 대상을 확인했습니다. `cmdline`과 `environ`의 항목은 NUL 문자로 구분되므로 단순 `cat` 출력은 서로 붙어 보일 수 있습니다. `tr`이 제공되는 펌웨어라면 `tr '\0' '\n'`으로 읽기 쉽게 변환할 수 있습니다.

관찰한 세션에서는 다음 결과를 얻었습니다.

```text
/proc/129/exe -> /bin/goahead
/proc/129/cmdline -> goahead
LD_LIBRARY_PATH=/mnt/mtd/lib
PATH=/mnt/mtd/run:/bin:/sbin:/usr/bin:/usr/sbin
MD5(/proc/129/exe) = 8ff6ebd74eafbb0f9db3dc6cec1209d9
```

정적 분석만으로는 appfs의 복사본이 실행될 가능성도 있었지만, `/proc/<PID>/exe` 심볼릭 링크를 확인하여 해당 세션에서 실제 실행된 파일은 `/bin/goahead`임을 확정했습니다. 다른 펌웨어에서는 경로가 달라질 수 있으므로 같은 절차를 반복해야 합니다.

### 5.6 SD 카드 쓰기 검증

```sh
mkdir -p /tmp/sd
mount -t vfat /dev/mmcblk0p1 /tmp/sd
echo DEVICE_SD_WRITE_OK > /tmp/sd/device_test.txt
sync
cat /tmp/sd/device_test.txt
```

`DEVICE_SD_WRITE_OK`가 다시 출력되어 실제 쓰기 가능함을 확인했습니다. `/opt`는 공간이 매우 작고 `/tmp`는 휘발성이므로, 크기가 큰 파일을 지속적으로 저장하려면 SD 카드와 같은 외부 저장공간이 필요합니다.

위 실험의 `/tmp/sd`는 쓰기 가능 여부를 확인하기 위해 임의로 만든 마운트 지점입니다. 제조사 애플리케이션 분석 기록에서는 `/dev/mmcblk0p1` 또는 `/dev/mmcblk0`을 `/mnt/sd_card`에 마운트하는 흐름이 확인되었습니다. 따라서 후속 기능에서 SD 카드를 사용할 때는 수동 검증 경로와 제품의 실제 운용 경로를 구분해야 합니다.

## 6. 정적 분석과의 교차검증

| 정적 분석 결과 | 동적 확인 | 결과 |
|---|---|---|
| PID 1은 `/linuxrc` 기반 init임 | `ps`에서 `{linuxrc} init` 확인 | 일치 |
| rootfs는 mtdblock3 SquashFS임 | `/proc/cmdline`, `/proc/mounts` 확인 | 일치 |
| appfs는 `/mnt/mtd`에 마운트됨 | mtdblock4의 read-only 마운트 확인 | 일치 |
| config는 `/opt`의 JFFS2임 | mtdblock5의 read-write 마운트 확인 | 일치 |
| `/mnt/mtd/lib`가 라이브러리 경로임 | `goahead`의 environ과 maps 확인 | 일치 |
| `goahead` 실행본은 appfs일 수 있음 | `/proc/<PID>/exe` 확인 | 해당 장비에서는 `/bin/goahead`로 확인됨 |
| 웹 루트 초기화가 필요함 | 버전별 syscall 비교 | null 경로 접근을 확인하고 초기화 함수 비교 대상으로 연결 |
| form 이름은 내부 callback과 연결됨 | `websFormDefine`의 이름·주소 인자 관찰 | 외부 입력과 관련된 callback 후보를 선별 |
| handler 이름은 service 함수와 연결됨 | `websDefineHandler`의 인자와 backtrace 관찰 | URI 처리 방식과 내부 service의 대응 확인 |

## 7. 동적 분석의 의의

정적 분석만으로는 여러 파티션에 있는 실행 파일 중 어느 복사본이 사용되는지, 어떤 환경 변수와 라이브러리가 적용되는지, 특정 설정과 입력에서 어느 코드 경로가 선택되는지를 확정하기 어렵습니다. 동적 분석은 QEMU의 실행 로그, GDB의 함수 관찰과 실기기의 `/proc`, `dmesg` 정보를 이용해 이러한 가설을 실제 실행 상태와 비교하는 역할을 합니다.

버전별 실행 로그의 차이는 초기화 함수의 비교로 연결했고, 요청 등록 과정에서는 외부 입력과 관련된 콜백 후보를 좁혔습니다. 이처럼 syscall은 “프로그램이 외부에 무엇을 요청했는가”를, 함수 중단점은 “그 동작을 만들기 위해 내부의 어느 코드가 실행되었는가”를 확인하는 데 사용합니다.

또한 에뮬레이션으로 확인할 수 있는 사용자 공간 동작과 실기기에서만 확인할 수 있는 드라이버·하드웨어 동작을 구분할 수 있습니다. 이를 통해 이후 단계에서 사용할 실행 파일, 라이브러리 경로, 저장 위치, 우선 분석할 함수와 검증 환경을 근거에 따라 결정할 수 있습니다.

## 8. 분석 결과

- 바이너리 형식에 맞춰 QEMU와 GDB를 선택하고, BusyBox 실행과 GDB 연결로 기본 분석 환경을 검증했습니다.
- rootfs와 config 영역을 구성하여 `goahead`가 요구하는 절대경로와 설정 의존성을 재현했습니다.
- 성공한 syscall 로그에서 라이브러리·설정 파일 적재, `bind`·`listen`·`accept`와 웹 문서 접근을 확인했습니다.
- 펌웨어 버전별 syscall 차이에서 null 문서 경로와 assertion을 확인하고, 정적 분석에서 검토할 초기화 함수로 범위를 좁혔습니다.
- Ghidra와 GDB에서 동일한 등록 함수를 확인하여 form·handler 이름과 내부 callback·service 후보의 대응 관계를 구성했습니다.
- 실기기에서 부팅 인자, 프로세스, 마운트, 메모리, 실행 파일 경로와 라이브러리 매핑을 확인했습니다.
- 커널 로그와 `/proc` 정보를 통해 MMC, ISP, IPU, Wi-Fi와 센서 드라이버의 초기화 상태를 확인했습니다.
- 관찰한 장비는 약 38MB의 RAM을 제공했으며, `/opt`는 설정 저장용으로는 사용할 수 있지만 대용량 파일을 저장하기에는 공간이 부족함을 확인했습니다.
- QEMU는 사용자 공간의 초기 실행과 오류 분석에 사용하고, 장치 드라이버와 하드웨어 의존 동작은 실기기에서 검증해야 함을 확인했습니다.

## 9. 재현 체크리스트

- [ ] `file`, `readelf`로 아키텍처, ABI와 동적 로더를 확인했습니다.
- [ ] `readelf -d`의 공유 라이브러리와 해당 심볼릭 링크가 rootfs에 존재하는지 확인했습니다.
- [ ] 실제 rootfs의 라이브러리와 설정 영역을 준비했습니다.
- [ ] 초기화 스크립트를 실행하기 전에 위험한 명령을 검토했습니다.
- [ ] BusyBox로 QEMU 환경을 먼저 검증했습니다.
- [ ] 대상 프로그램에 재현용 요청이나 실행 인자를 전달하고 syscall 로그를 저장했습니다.
- [ ] 정상·비정상 버전의 로그를 같은 조건에서 비교했습니다.
- [ ] Ghidra의 문자열·XRef 결과와 동적 오류를 연결했습니다.
- [ ] 등록 관찰 결과와 실제 요청 도달 검증을 구분하여 기록했습니다.
- [ ] `/proc/<PID>/exe`, `cmdline`, `environ`, `maps`로 실기기 상태를 확인했습니다.
- [ ] 저장공간과 메모리의 실행 전후 값을 비교했습니다.
- [ ] QEMU 결과를 실기기에서 최종 검증했습니다.

## 10. 한계

- QEMU user-mode는 사용자 공간 프로그램 분석 환경이며 카메라 보드 전체를 에뮬레이션하지 않습니다.
- 센서, ISP, Wi-Fi와 전용 커널 모듈의 동작은 실기기에서만 확인할 수 있습니다.
- 일부 측정값은 특정 펌웨어와 한 시점의 프로세스 상태에 해당합니다.
- GDB로 등록 함수의 이름과 callback·service 인자를 확인했지만, 모든 form에 실제 HTTP 요청을 보내 각 callback 도달과 응답까지 검증한 것은 아닙니다.
