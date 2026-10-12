# inittab

앞서 rcS 파일을 수정하여 Telnet 서버가 자동으로 실행되도록 설정하는 방법을 알아봤습니다. 본 문서에서는 rcS를 수정하지 않고 inittab 파일을 통해 Telnet 서버를 실행하도록 설정하는 방법에 대해서 다뤄보겠습니다.

## inittab 스크립트 분석 및 수정

### inittab 스크립트

inittab은 리눅스 시스템의 초기화 프로세스인 init이 시스템 부팅 시 어떤 프로그램을 실행할지 정의하는 설정 파일입니다.

우리가 사용하는 펌웨어의 경우에는 전원이 공급되면 부트로더가 실행되고 이후 리눅스 커널이 실행됩니다. 커널이 초기화가 완료되면 init 프로세스가 실행되며 초기화 시스템의 종류에 따라 /etc/inittab 등의 설정 파일을 읽어 시스템 초기화에 필요한 프로그램을 실행합니다.

앞서 확인한 바로는 BusyBox의 init을 사용하는 구조로, inittab 파일을 통해 초기화 스크립트인 rcS와 기타 프로그램을 실행하도록 구성되어 있습니다.

따라서, 앞서 분석한 rcS가 실제 시스템 초기화 작업을 수행하는 스크립트라면, inittab는 이러한 초기화 스크립트와 프로그램을 언제, 어떤 방식으로 실행할지 지정하는 설정 파일입니다.

### inittab 스크립트 분석

먼저, 펌웨어 분석 과정에서 알게 된 inittab 파일 경로인 ./squashfs-root/etc/inittab를 확인합니다.

```
cat ./squashfs-root/etc/inittab
```

inittab은 다음과 같은 형식으로 작성됩니다.

```
<id>:<runlevels>:<action>:<process>
```

각 항목의 의미는 다음과 같습니다.

- id : 프로그램을 실행할 터미널 식별자
- runlevels : 실행 레벨을 지정하는 필드
- action : 프로그램의 실행 시점 및 실행 방식
    - sysinit : 시스템 초기화 단계에서 실행하며 종료될 때까지 대기
    - respawn : 프로그램이 종료되면 자동으로 다시 실행
    - once : 프로그램을 한 번 실행하고 종료를 기다리지 않음
    - shutdown : 시스템 종료 과정에서 실행
- process : 실제 실행할 명령어 또는 프로그램

이를 바탕으로 실제 inittab에 작성된 명령어를 살펴보면 다음과 같습니다.

```shell
# Startup the system
::sysinit:/bin/mount -t tmpfs tmpfs /dev
::sysinit:/bin/mkdir -p /dev/pts
::sysinit:/bin/mkdir -p /dev/shm
::sysinit:/bin/mount -a
::sysinit:/bin/hostname -F /etc/hostname
```

위 코드는 시스템 부팅 과정에서 필요한 디렉터리와 파일시스템을 설정하는 초기화 명령어입니다.

해당 명령어들은 모두 sysinit으로 지정되어 있으므로 시스템 초기화 단계에서 실행됩니다.

```shell
# now run any rc scripts
::sysinit:/etc/init.d/rcS
```

위 명령어는 앞서 분석한 rcS 초기화 스크립트를 실행하는 부분입니다.

따라서 BusyBox의 init은 시스템 초기화 과정에서 rcS를 실행하고, 해당 스크립트가 종료될 때까지 기다립니다.

이 과정을 통해 rcS에 작성된 네트워크 설정, 파일시스템 마운트 및 웹 서버 실행 등의 작업이 수행됩니다.

이를 통해 앞에서 분석한 rcS가 inittab에 의해 실행되도록 설정되어 있음을 확인할 수 있습니다.

```shell
# Put a getty on the serial port
console::respawn:/sbin/getty -L console 115200 vt100 # GENERIC_SERIAL
```

해당 명령어는 시리얼 콘솔을 통한 사용자 접속을 처리하는 getty 프로그램을 실행합니다.

```shell
# Stuff to do before rebooting
::shutdown:/bin/umount -a -r
```

위 명령어는 시스템 종료 과정에서 마운트된 파일시스템을 정리하기 위한 설정입니다.

이처럼 inittab은 시스템 초기화부터 콘솔 관리 및 종료 과정까지 프로그램의 실행 방식을 지정하는 역할을 합니다.

### inittab 스크립트 수정

앞서 분석한 rcS는 inittab에 의해 실행되는 초기화 스크립트이므로, rcS에 /sbin/telnetd & 명령어를 추가했다면 inittab을 별도로 수정하지 않아도 장비 부팅 시 Telnet 서버를 실행하도록 구성할 수 있습니다.

반대로 rcS를 수정하지 않고 inittab에 ::once:/sbin/telnetd 항목을 추가하는 방법도 있습니다.

따라서 두 가지 방법 중 하나를 선택하여 적용하면 되며, 두 파일에 모두 Telnet 서버 실행 명령어를 추가할 경우 동일한 서비스가 중복 실행되어 포트 충돌 등의 문제가 발생할 수 있으므로 주의해야 합니다.

앞선 문서와 해당 문서에선 두 가지 방법을 모두 설명하지만, 실제 적용 시에는 하나의 방법만 선택하여 사용하면 됩니다.

우선 다음과 같이 squashfs-root/etc/inittab 스크립트 파일을 열어 수정해줍니다.

```
sudo nano ./squashfs-root/etc/inittab
```

```shell
# /etc/inittab
#
# Copyright (C) 2001 Erik Andersen <andersen@codepoet.org>
#
# Note: BusyBox init doesn't support runlevels.  The runlevels field is
# completely ignored by BusyBox init. If you want runlevels, use
# sysvinit.
#
# Format for each entry: <id>:<runlevels>:<action>:<process>
#
# id        == tty to run on, or empty for /dev/console
# runlevels == ignored
# action    == one of sysinit, respawn, askfirst, wait, and once
# process   == program to run

# Startup the system
::sysinit:/bin/mount -t tmpfs tmpfs /dev
::sysinit:/bin/mkdir -p /dev/pts
::sysinit:/bin/mkdir -p /dev/shm
::sysinit:/bin/mount -a
::sysinit:/bin/hostname -F /etc/hostname

# now run any rc scripts
::sysinit:/etc/init.d/rcS

# 해당 부분을 inittab에 추가
::once:/sbin/telnetd

# Put a getty on the serial port
console::respawn:/sbin/getty -L console 115200 vt100 # GENERIC_SERIAL

# Stuff to do for the 3-finger salute
#::ctrlaltdel:/sbin/reboot

# Stuff to do before rebooting
::shutdown:/bin/umount -a -r
```

추가한 명령어의 의미는 다음과 같습니다.

```
::once:/sbin/telnetd
```

- once : 프로그램을 한 번 실행하고 종료될 때까지 기다리지 않으며, 종료되더라도 자동으로 재실행하지 않습니다.
- /sbin/telnetd : 앞서 확인한 BusyBox의 Telnet 서버 실행 경로입니다.

즉, 시스템 초기화 이후 Telnet 서버를 실행하도록 설정할 수 있습니다.

### 주의사항

이처럼 inittab의 once 항목을 활용하면 rcS를 직접 수정하지 않고도 부팅 과정에서 Telnet 서버를 시작하도록 구성할 수 있습니다.

단, 앞서 설명한 것처럼 rcS와 inittab에 동일한 Telnet 서버 실행 명령어를 중복으로 추가할 필요는 없으며, 실제 적용 시에는 하나의 방법만 선택해야 합니다.
