# rcS

앞에서 펌웨어 추출 과정을 통해 확보한 펌웨어를 기반으로, 본 문서에서는 실제 장비 내부에 접속할 수 있는 분석 환경을 만들기 위해 펌웨어의 rcS 파일을 수정하는 방법에 대해서 다룹니다.

## telnetd 확인 및 /etc/shadow 수정

### telnetd 확인

파일 시스템 내에 telnetd 명령어가 있는 경우, IoT 기기의 부팅 스크립트에서 telnetd를 실행하면 장비가 켜질 때 telnet 서버가 자동을 시작되도록 하면서 실제 장비 내부에 접속할 수 있게 됩니다.

따라서, 우선 파일 시스템에 아래와 같이 telnetd 명령어가 존재하는지 확인할 수 있습니다.

```
find ./ -name "telnetd" 2>/dev/null
```

```
ls -al ./sbin/telnetd
```

![](./image01.png)

파일 시스템에 telnetd과 관련된 파일을 찾고, 해당 파일이 ../bin/busybox를 가리키는 심볼릭 링크임을 확인하면서, 펌웨어에 telnetd 명령어가 존재함을 알 수 있습니다.

### /etc/shadow 수정

telnet 접속 시 비밀번호 없이 root로 접속할 수 있게 하기 위해 파일 시스템에서 /etc/shadow 파일을 수정해줍니다.

여기서 /etc/shadow는 사용자 계정의 비밀번호와 관련된 정보를 저장하는 시스템 설정 파일입니다.

/etc/shadow 파일을 수정 시에는 `sudo`를 붙여야 내용을 수정할 수 있습니다.

```
sudo vi squashfs-root/etc/shadow
```

**수정 전 /etc/shadow**

```
root:$5$HvUmiKay8JugO17C$gazQrgfxANwpkKuzhKvE0.KVTWrS53cyVLsm8yiSkrC:10933:0:99999:7:::
```

**수정 후 /etc/shadow**

```
root::10933:0:99999:7:::
```

root: 다음에 나오는 두번째 필드에 해당하는 값이 비밀번호 해시값이므로 해당 값을 지워 비밀번호 없이 로그인이 가능하도록 해줍니다.

## rcS 시스템 초기화 스크립트

rcS는 시스템 부팅 시 실행되는 초기화 스크립트로, 장비가 정상적으로 동작하기 위해서 필요한 서비스와 프로그램을 실행하는 역할을 합니다.

장비가 켜질 때 telnet 서버가 자동으로 시작되도록 만들 것이기 때문에, 해당 rcS에 telnet을 실행시킬 수 있는 명령어를 추가해주면 자동으로 실행하도록 설정할 수 있습니다.

### rcS 수정

앞서 확인한 BusyBox의 telnetd 기능을 아래와 같이 초기화 스크립트에 넣어줍니다.

```shell
sudo nano ./etc/init.d/rcS
```

```bash
goahead &
if [ $? -eq 0 ]; then
        echo "goahead running ......"
fi

system_call_daemon &
if [ $? -eq 0 ]; then
        echo "system_call_daemon running ......"
fi

# Run start script
if [ -f /mnt/mtd/startapp ]; then
        echo "==> startapp ok"
    /mnt/mtd/startapp &
fi

# ./etc/init.d/rcS 파일의 마지막줄에 /sbin/telnetd & 추가
/sbin/telnetd &
```
