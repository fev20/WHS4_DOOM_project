# 업데이트 적용

카메라의 루트 파일시스템은 읽기 전용으로 설계되어 있어 DOOM 포팅을 위해 수정하였던 goahead, inittab, rcS 등의 변경점을 적용하기 위해서는 단순히 Telnet으로 접속하여 파일을 복사하거나 수정하는 방식으로 진행할 수는 없습니다.

따라서 펌웨어 업데이트를 통해서 변경점을 적용해야 합니다. 앞선 [업데이트 로직 분석](../../펌웨어%20분석/업데이트%20로직%20분석/README.md)에서 확인한 파일 형식에 맞춰 수정한 파일을 다시 묶은 뒤, 카메라에 업로드합니다.

## 1. 업데이트 파일 준비

먼저 PC에서 수정한 루트 파일시스템을 원본과 같은 SquashFS 형식으로 다시 묶습니다. 이때 파일의 실행 권한과 심볼릭 링크를 유지해야 합니다.

```bash
mkdir -p repacked
mksquashfs modified_firmware_unpacked/rootfs repacked/rootfs.squashfs \
  -comp xz -b 131072 -all-root -no-xattrs -noappend
```

`-all-root`는 파일 소유자를 root로 지정하고, `-noappend`는 기존 이미지에 내용을 덧붙이지 않고 새로 생성하는 옵션입니다. 생성된 이미지의 설정은 다음 명령으로 확인합니다.

```bash
unsquashfs -s repacked/rootfs.squashfs
```

생성한 이미지는 그대로 업로드하지 않고, 카메라가 읽을 수 있는 업데이트 파일로 구성합니다. rootfs, 커널, 카메라 프로그램, 업데이트 도구를 각 푸터와 함께 묶고, 파일 앞에 전체 헤더를 붙입니다. 변경한 데이터의 크기와 MD5도 다시 계산하여 반영합니다.

수정한 rootfs를 원본 덤프에 반영한 `repacked_firmware.bin`을 준비한 뒤, `repack_firmware.py`와 공식 펌웨어가 있는 폴더에서 다음 명령을 실행합니다. 이 스크립트는 rootfs 폴더를 직접 읽지 않으므로, 먼저 덤프에 수정 내용을 반영해야 합니다.

```bash
uv run repack_firmware.py \
  repacked_firmware.bin A12_IronMan_05.02.31.114.img output.img
```

입력 순서는 수정한 8 MiB 덤프, 공식 펌웨어, 출력 파일입니다. 실행하면 `output.img`와 검사 정보인 `output.img.json`이 생성됩니다. 같은 이름의 출력 파일이 이미 있다면 다른 이름을 지정합니다.

이후 절차에서는 이렇게 준비한 업데이트 파일의 이름을 `output.img`로 사용합니다. 업로드 전에는 장비 모델과 파일 형식이 맞는지 확인하고, 원본 펌웨어를 따로 보관합니다.

## 2. 카메라에 업로드

PC를 카메라와 같은 네트워크에 연결한 뒤, `output.img`가 있는 폴더에서 다음 명령을 실행합니다. IP 주소는 자신의 카메라 주소로 바꿉니다.

```bash
curl -i \
  -F 'filename=@./output.img' \
  -F 'UploadFirmwareSubmit=Apply' \
  http://192.168.0.214/cgi-bin/upload_app.cgi
```

`filename`에는 업데이트 파일을, `UploadFirmwareSubmit`에는 적용을 요청하는 값인 `Apply`를 전달합니다. 관리자 페이지가 열리지 않아도 분석에서 확인한 업로드 주소로 요청을 보낼 수 있습니다.

응답에 `Done...rebooting`이 표시되는지 확인하고, 업데이트와 재부팅이 끝날 때까지 전원을 유지합니다. 오류가 발생한 경우에도 재부팅될 수 있으므로, 재부팅 여부만으로 적용 성공을 판단하지 않습니다.

## 3. 변경 사항 확인

재부팅 후 카메라에 다시 접속하여 수정한 내용이 반영되었는지 확인합니다.

- **rcS**: 부팅 후 Telnet으로 접속할 수 있는지 확인합니다.
- **inittab**: 수정한 항목에 해당하는 부팅 동작을 확인합니다.
- **goahead**: 웹 서버의 수정한 설정이 반영되었는지 확인합니다.

접속 후 `/etc/init.d/rcS`의 수정 내용도 확인합니다. 업데이트 응답과 재부팅 후 실제 동작을 함께 확인하여 변경 사항의 적용 여부를 판단합니다.
