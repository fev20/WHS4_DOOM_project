# 4-1. rcS

앞에서 펌웨어 추출 과정을 통해 확보한 펌웨어를 기반으로, 본 문서에서는 실제 장비 내부에 접속할 수 있는 분석 환경을 만들기 위해 펌웨어의 rcS 파일을 수정하는 방법에 대해서 다룹니다.

## 4-1-0. telnetd 확인 및 /etc/shadow 수정

### 1. telnetd 확인

```
find ./ -name "telnetd" 2>/dev/null
```

```
ls -al ./sbin/telnetd
```

![](./images/04-01-01_telnetd.png)

파일 시스템 내에 telnetd 명령어를 확인 후 해당 명령어가 존재함을 확인할 수 있다.

### 2. /etc/shadow 수정

root 계정의 비밀번호를 제거해 telnet 접속 시 인증 없이 바로 접속할 수 있도록 변조해줬습니다.

**수정 전 /etc/shadow**

```
root:$5$HvUmiKay8JugO17C$gazQrgfxANwpkKuzhKvE0.KVTWrS53cyVLsm8yiSkrC:10933:0:99999:7:::
```

**수정 후 /etc/shadow**

```
root::10933:0:99999:7:::
```

## 4-1-1. rcS 수정

rcS 부팅 스크립트에서 명령어를 실행하도록 수정했습니다.

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

/sbin/telnetd &
```
