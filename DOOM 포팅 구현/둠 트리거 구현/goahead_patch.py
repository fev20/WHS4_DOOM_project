import struct

# ===== 설정 =====
FIRMWARE_PATH = "goahead"      # 원본(패치 안 된) 바이너리로 실행 권장
OUTPUT_PATH   = "goahead_patched"

FUNC_START_VA = 0x0040F280   # FUN_0040f280 (gp복원 스텁 시작)
FUNC_END_VA   = 0x0040F444   # websLogoutUser 시작 (= 패치 대상 끝)

STRING_DATA = b"/etc/webs/trigger\x00"   # 18바이트

# ===== 명령어 워드 목록 (전부 실제 원본/검증된 인코딩) =====
INSTR_WORDS = [
    0x3C1C0006,  # lui   gp, 0x6                (원본 그대로)
    0x279C8AD0,  # addiu gp, gp, -0x7530         (원본 그대로)
    0x0399E021,  # addu  gp, gp, t9              (원본 그대로)
    0x27BDFFD0,  # addiu sp, sp, -0x30
    0xAFBF002C,  # sw    ra, 0x2c(sp)
    0x3C040040,  # lui   a0, 0x40
    0x3484F2B8,  # ori   a0, a0, 0xf2b8          <- 문자열 주소 (아래서 재검증)
    0x8F998888,  # lw    t9, -0x7778(gp)         => system
    0x0320F809,  # jalr  t9
    0x00000000,  # nop                            (delay slot, 필수)
    0x8FBF002C,  # lw    ra, 0x2c(sp)
    0x27BD0030,  # addiu sp, sp, 0x30
    0x03E00008,  # jr    ra
    0x00000000,  # nop                            (delay slot, 필수)
]

def build_patch_bytes():
    code = b"".join(struct.pack("<I", w) for w in INSTR_WORDS)
    code_len = len(code)
    string_va = FUNC_START_VA + code_len

    # ori a0,a0,IMM 의 IMM이 실제 문자열 주소 하위 16비트와 일치하는지 검증
    expected_imm = string_va & 0xFFFF
    baked_imm = INSTR_WORDS[6] & 0xFFFF
    if expected_imm != baked_imm:
        raise ValueError(
            f"ori 명령어의 offset(0x{baked_imm:04X})이 실제 문자열 주소"
            f"(0x{string_va:08X}, 하위16비트 0x{expected_imm:04X})와 안 맞음! "
            f"INSTR_WORDS[6]을 0x3484{expected_imm:04X}로 고쳐야 함."
        )
    # lui a0,HI 도 검증 (혹시 페이지 경계 넘어가면 HI값도 조정 필요)
    expected_hi = string_va >> 16
    baked_hi = INSTR_WORDS[5] & 0xFFFF
    if expected_hi != baked_hi:
        raise ValueError(
            f"lui a0,HI값(0x{baked_hi:04X})이 실제 문자열 주소 상위16비트"
            f"(0x{expected_hi:04X})와 안 맞음."
        )

    pad_len = (4 - (len(STRING_DATA) % 4)) % 4
    string_block = STRING_DATA + b"\x00" * pad_len

    nop_start = string_va + len(string_block)
    nop_total_len = FUNC_END_VA - nop_start
    if nop_total_len < 0:
        raise ValueError("계산 오류: NOP 채울 공간이 음수. 주소/길이 재확인 필요.")
    if nop_total_len % 4 != 0:
        raise ValueError(f"NOP 채울 길이({nop_total_len})가 4의 배수가 아님.")

    nops = struct.pack("<I", 0) * (nop_total_len // 4)

    patch = code + string_block + nops
    assert len(patch) == FUNC_END_VA - FUNC_START_VA, \
        f"패치 크기 불일치: {len(patch)} != {FUNC_END_VA - FUNC_START_VA}"

    return patch, string_va

# ===== ELF 프로그램 헤더 파싱 (VA -> 파일 오프셋) =====
def parse_elf_load_segments(data: bytes):
    if data[:4] != b"\x7fELF":
        raise ValueError("ELF 매직 넘버가 아님")
    ei_class = data[4]     # 1=32bit, 2=64bit
    ei_data  = data[5]     # 1=LSB(little), 2=MSB(big)
    endian = "<" if ei_data == 1 else ">"

    if ei_class == 1:  # ELF32
        e_phoff, e_phentsize, e_phnum = struct.unpack_from(endian + "I", data, 0x1C)[0], \
                                         struct.unpack_from(endian + "H", data, 0x2A)[0], \
                                         struct.unpack_from(endian + "H", data, 0x2C)[0]
        segments = []
        for i in range(e_phnum):
            base = e_phoff + i * e_phentsize
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
                struct.unpack_from(endian + "8I", data, base)
            if p_type == 1:  # PT_LOAD
                segments.append((p_offset, p_vaddr, p_filesz))
        return segments
    else:  # ELF64
        e_phoff = struct.unpack_from(endian + "Q", data, 0x20)[0]
        e_phentsize = struct.unpack_from(endian + "H", data, 0x36)[0]
        e_phnum = struct.unpack_from(endian + "H", data, 0x38)[0]
        segments = []
        for i in range(e_phnum):
            base = e_phoff + i * e_phentsize
            p_type, p_flags = struct.unpack_from(endian + "2I", data, base)
            p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
                struct.unpack_from(endian + "6Q", data, base + 8)
            if p_type == 1:
                segments.append((p_offset, p_vaddr, p_filesz))
        return segments

def va_to_file_offset(segments, va: int) -> int:
    for p_offset, p_vaddr, p_filesz in segments:
        if p_vaddr <= va < p_vaddr + p_filesz:
            return p_offset + (va - p_vaddr)
    raise ValueError(f"VA 0x{va:08X}를 포함하는 PT_LOAD 세그먼트를 못 찾음")

def main():
    with open(FIRMWARE_PATH, "rb") as f:
        data = bytearray(f.read())

    segments = parse_elf_load_segments(bytes(data))
    print("[+] PT_LOAD 세그먼트:")
    for off, vaddr, filesz in segments:
        print(f"    VA=0x{vaddr:08X}~0x{vaddr+filesz:08X}  file_off=0x{off:08X}")

    patch, string_va = build_patch_bytes()
    print(f"[+] 문자열 실제 배치 주소: 0x{string_va:08X}")
    print(f"[+] 패치 전체 크기: {len(patch)} 바이트 (원본: {FUNC_END_VA - FUNC_START_VA})")

    file_off = va_to_file_offset(segments, FUNC_START_VA)
    print(f"[+] VA 0x{FUNC_START_VA:08X} -> 파일 오프셋 0x{file_off:X}")

    data[file_off:file_off + len(patch)] = patch

    with open(OUTPUT_PATH, "wb") as f:
        f.write(data)
    print(f"[+] 패치 완료 -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
