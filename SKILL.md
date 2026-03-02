---
name: use-hwpx
description: "울산광역시교육청 전용 HWPX 문서 생성/읽기/편집 스킬. 공문, 업무보고서, 회의록, 기안문 4종 지원."
---

# 울산광역시교육청 HWPX 문서 스킬

울산광역시교육청 전용 한글(HWPX) 문서를 **XML 직접 작성** 방식으로 생성, 편집, 읽기하는 스킬.
4가지 문서 유형(공문, 업무보고서, 회의록, 기안문)을 지원하며, 기관 정보는 템플릿에 하드코딩되어 있다.

## 기관 정보 (하드코딩)

| 항목 | 값 |
|------|-----|
| 기관명 | 울산광역시교육청 |
| 주소 | 울산광역시 중구 북부순환도로 375(유곡동) |
| 우편번호 | 44540 |
| 홈페이지 | www.use.go.kr |

## 환경

```
SKILL_DIR="이 SKILL.md가 위치한 디렉토리의 절대 경로"
VENV="<프로젝트>/.venv/bin/activate"
```

모든 Python 실행 시:
```bash
source "$VENV"   # lxml이 없으면 스크립트가 자동으로 pip install lxml 실행
```

## 디렉토리 구조

```
use-hwpx/
├── SKILL.md                               # 이 파일
├── scripts/
│   ├── office/
│   │   ├── unpack.py                      # HWPX → 디렉토리 (XML pretty-print)
│   │   └── pack.py                        # 디렉토리 → HWPX
│   ├── build_hwpx.py                      # 템플릿 + XML → .hwpx 조립 (핵심)
│   ├── analyze_template.py                # HWPX 심층 분석
│   ├── validate.py                        # HWPX 구조 검증
│   └── text_extract.py                    # 텍스트 추출
├── templates/
│   ├── base/                              # 베이스 템플릿 (HWPX 골격)
│   ├── gonmun/                            # 공문 (header.xml + section0.xml)
│   ├── report/                            # 업무보고서 (BinData 이미지 포함)
│   │   └── BinData/                       # image1.bmp, image2.png, image3.jpg
│   ├── minutes/                           # 회의록
│   └── draft/                             # 기안문 (결재라인 포함)
├── examples/                              # 예제 .hwpx 파일
│   ├── gonmun_sample.hwpx
│   ├── report_sample.hwpx
│   ├── minutes_sample.hwpx
│   └── draft_sample.hwpx
└── references/
    └── hwpx-format.md                     # OWPML XML 요소 레퍼런스
```

---

## 워크플로우 1: 공문 (gonmun) 생성

```bash
source "$VENV"

# 기본 공문 (플레이스홀더 포함)
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun --output gonmun.hwpx

# 커스텀 section0.xml 사용
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun --section my_section0.xml --output gonmun.hwpx

# 메타데이터 포함
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun --section my_section0.xml \
  --title "업무협조 요청" --creator "교육혁신과" --output gonmun.hwpx

# 플레이스홀더 자동 치환 (--replace "키=값", 반복 가능)
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun \
  --replace "수신자=OO학교장" --replace "제목=업무협조 요청" \
  --replace "본문1=귀 기관의 무궁한 발전을 기원합니다." \
  --title "업무협조 요청" --creator "교육혁신과" --output gonmun.hwpx

# 검증
python3 "$SKILL_DIR/scripts/validate.py" gonmun.hwpx
```

### 공문 section0.xml 구조

| 문단 | paraPr | charPr | 내용 |
|------|--------|--------|------|
| 1 | 0 | 0 | [secPr + colPr] |
| 2 | 0 | 0 | 빈 줄 |
| 3 | 20 | 7 | **울산광역시교육청** (22pt 볼드, 가운데) ← 하드코딩 |
| 4 | 0 | 0 | 빈 줄 |
| 5 | 0 | 0 | 수 신 : {{수신자}} |
| 6 | 0 | 0 | (경유) {{경유}} |
| 7 | 0 | 0 | 제 목 {{제목}} |
| 8 | 0 | 0 | 빈 줄 |
| 9-10 | 0 | 0 | 본문 플레이스홀더 |
| 12 | 20 | 0 | - 아 래 - (가운데) |
| 14 | 0 | 0 | {{표 또는 상세내용}} |
| 16 | 20 | 0 | 끝. (가운데) |
| 19 | 20 | 8 | {{직위 성명}} (16pt 볼드) |
| 22-26 | 0 | 9 | 하단 시행 정보 |
| 25 | 0 | 9 | 우 44540 / ... / www.use.go.kr ← 하드코딩 |

---

## 워크플로우 2: 업무보고서 (report) 생성

report 템플릿에는 BinData 이미지(image1.bmp, image2.png, image3.jpg)와 전용 content.hpf가 포함되어 있다.
`build_hwpx.py`는 템플릿에 BinData/ 디렉토리나 content.hpf가 있으면 자동으로 복사한다.

```bash
source "$VENV"

# 기본 report (플레이스홀더 포함, 이미지 포함)
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report --output report.hwpx

# 플레이스홀더 치환 + 메타데이터
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report \
  --replace "작성일=2026. 3. 2.(월)" --replace "부서=총무과" \
  --replace "직위=주무관" --replace "작성자=홍길동" --replace "연락처=1234" \
  --replace "섹션1 제목=추진 배경" --replace "본문 내용=교육환경 개선 사업 추진" \
  --replace "세부 내용=노후 교실 리모델링" --replace "비고=예산 확보 완료" \
  --replace "섹션2 제목=추진 계획" --replace "표 제목=세부 추진 일정" \
  --title "교육환경 개선 보고" --creator "총무과" --output report.hwpx

# 커스텀 section0.xml 사용 (서식은 유지, 내용만 교체)
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report --section my_section0.xml \
  --title "교육환경 개선 보고" --creator "시설과" --output report.hwpx

# 검증
python3 "$SKILL_DIR/scripts/validate.py" report.hwpx
```

### 보고서 section0.xml 구조 (업무보고서 서식 기반)

이 서식은 울산광역시교육청 표준 업무보고서 양식을 기반으로, 머리글/로고 이미지, 도형 방식 목차 체계, 표 서식이 반영된 템플릿이다.

| 문단 | paraPr | charPr | 내용 |
|------|--------|--------|------|
| 1 | 18 | — | [secPr + colPr + 머리글 이미지(image1, PIC)] |
| 2 | 14 | — | 빈 줄 |
| 3 | 19 | 13 | (공백) |
| 4 | 12 | — | [PIC 로고(image2)] |
| 5 | 12 | 13 | {{작성일}}  {{부서}} {{직위}} {{작성자}} ☏{{연락처}} |
| 6 | 16 | 7/8 | 󰏚 {{섹션1 제목}} (HY헤드라인M 16pt) |
| 7 | 17 | 9 | ❍ {{본문 내용}} (휴먼명조 15pt) |
| 8 | 17 | 9 | - {{세부 내용}} (휴먼명조 15pt) |
| 9 | 17 | 10 | ※ {{비고}} (중고딕 13pt) |
| 10 | 17 | 7/8 | 󰏚 {{섹션2 제목}} (HY헤드라인M 16pt) |
| 11 | 17 | 9 | ❍ {{본문 내용}} (휴먼명조 15pt) |
| 12 | 17 | 9 | ❍ {{표 제목}} + [TABLE 2x2] + [PIC 구분선(image3)] |

### BinData (이미지) 구조

report 템플릿의 `BinData/` 디렉토리:

| 파일 | 용도 | 형식 |
|------|------|------|
| image1.bmp | 머리글 배경/로고 | BMP |
| image2.png | 제목 영역 로고 | PNG |
| image3.jpg | 구분선/장식 | JPEG |

content.hpf의 `<opf:manifest>`에 이미지가 등록되어 있어야 한글 프로그램이 인식한다.

### 업무보고서 서식 작성방법

> 출처: `업무보고서 서식 작성방법.hwpx` (울산광역시교육청 표준 가이드)

#### 본문 서식

| 항목 | 규격 | HWPUNIT 환산 |
|------|------|-------------|
| 편집여백 (좌‧우) | 20mm | 5669 |
| 편집여백 (위‧아래) | 10mm | 2834 |
| 머리말‧꼬리말 | 10mm | 2834 |
| **본문폭** | **170mm** | **48190** (= 59528 - 5669×2) |
| 글자체 (본문) | 휴먼명조 15pt | charPr 9, 1500 |
| 글자체 (제목) | HY헤드라인M 16pt | charPr 8, 1600 |
| 자간 | –5% | spacing=-5 |
| 장평 | 100% | ratio=100 |
| 문단간격 | 임의 설정 가능 | — |

**주의**: report 템플릿의 본문폭(48190)은 base/gonmun/minutes/draft(42520)와 다름. 표 너비 계산 시 주의.

#### 목차 체계 (두 가지 방식)

**도형 방식** (기본 서식에 포함):
```
󰏚 섹션 제목          ← charPr 7/8, HY헤드라인M 16pt, paraPr 16
  ❍ 본문              ← charPr 9, 휴먼명조 15pt, paraPr 17
    - 세부 내용        ← charPr 9, 휴먼명조 15pt, paraPr 17
      ※ 비고/참고      ← charPr 10, 중고딕 13pt, paraPr 17
```

**번호 붙임 방식** (서식 하단에 포함):
```
1. 섹션 제목           ← charPr 8, HY헤드라인M 16pt, paraPr 16
  가. 소제목           ← charPr 9, 휴먼명조 15pt, paraPr 17
  나. 소제목           ← charPr 9, 휴먼명조 15pt, paraPr 17
2. 섹션 제목           ← charPr 8, HY헤드라인M 16pt, paraPr 16
  가. ...
```

#### 표 서식

- **글꼴**: 맑은고딕 12pt 또는 휴먼명조 12pt
- **표 너비**: 본문폭(48190) 이내, 샘플 표는 3열×3행 (열너비 12120×3 = 36360)
- **셀 여백**: left/right 510, top/bottom 141
- **테두리**: borderFillIDRef로 참조 (헤더 셀과 본문 셀 구분)

#### 내용 작성 규칙

- **핵심 내용만 기재**, 단 항목은 빠짐없이 기술 (참고자료는 별첨)
- 강조할 부분은 **진하게** 또는 **파랑색** 표시

#### 행정 사항

- 업무보고 및 회의자료 제출 시 **안내된 서식으로 통일**
  - 대상: 월요정책회의, 간부회의, 코로나19 대응 비상회의 등
- **슬로건, 제목 서식, 담당자 정보 등 변경 금지**

---

## 워크플로우 3: 회의록 (minutes) 생성

```bash
source "$VENV"

python3 "$SKILL_DIR/scripts/build_hwpx.py" --template minutes --output minutes.hwpx
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template minutes --section my_section0.xml \
  --title "정례 회의록" --creator "기획조정과" --output minutes.hwpx
python3 "$SKILL_DIR/scripts/validate.py" minutes.hwpx
```

### 회의록 section0.xml 구조

| 문단 | paraPr | charPr | 내용 |
|------|--------|--------|------|
| 1 | 0 | 0 | [secPr + colPr] |
| 3 | 20 | 0 | 울산광역시교육청 (가운데) ← 하드코딩 |
| 4 | 20 | 7 | {{회의록 제목}} (18pt 볼드, 가운데) |
| 6 | 0 | — | [메타데이터 표 4행x2열] |
| | | | 열너비: 8504 + 34016 = 42520 |
| | | | Row 0: 일시 / {{YYYY년 MM월 DD일 HH:MM}} |
| | | | Row 1: 장소 / {{장소}} |
| | | | Row 2: 참석자 / {{참석자 목록}} |
| | | | Row 3: 작성자 / {{작성자}} |
| 9+ | 0 | 8/0 | 안건 → 논의 내용 → 결정 사항 → 향후 조치 |

---

## 워크플로우 4: 기안문 (draft) 생성

```bash
source "$VENV"

python3 "$SKILL_DIR/scripts/build_hwpx.py" --template draft --output draft.hwpx
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template draft --section my_section0.xml \
  --title "교육과정 운영 기안" --creator "교육과정과" --output draft.hwpx
python3 "$SKILL_DIR/scripts/validate.py" draft.hwpx
```

### 기안문 section0.xml 구조

| 문단 | paraPr | charPr | 내용 |
|------|--------|--------|------|
| 1 | 0 | 0 | [secPr + colPr] |
| 3 | 0 | — | [결재라인 표 5행x4열, 우측 정렬, 너비=22680] |
| | | | Row 0: "결재" (4열 병합, #E7E7E7 배경) |
| | | | Row 1: 담당 / 팀장 / 과장 / 국장 (#E7E7E7 배경) |
| | | | Row 2: 서명 영역 (빈 셀, 높이=4000) |
| | | | Row 3: {{담당자명}} / {{팀장명}} / {{과장명}} / {{국장명}} |
| | | | Row 4: {{일자}} x4 |
| | | | 열너비: 5670 x 4 = 22680 |
| 5 | 20 | 7 | **울산광역시교육청** (22pt 볼드, 가운데) ← 하드코딩 |
| 7-9 | 0 | 0 | 수신, 경유, 제목 |
| 11-12 | 0 | 0 | 본문 |
| 14 | 20 | 0 | - 아 래 - |
| 18 | 20 | 0 | 끝. |
| 21 | 20 | 8 | {{직위 성명}} (16pt 볼드) |
| 27 | 0 | 9 | 우 44540 / ... / www.use.go.kr ← 하드코딩 |

### 결재라인 커스터마이징

결재라인 열 수를 변경하려면 section0.xml의 표 구조를 수정:

- **3인 결재**: 열 3개, 열너비 7560 x 3 = 22680
- **5인 결재**: 열 5개, 열너비 4536 x 5 = 22680
- Row 0의 colSpan을 열 수에 맞춰 변경
- Row 1~4의 셀 수를 열 수에 맞춰 추가/제거

---

## 워크플로우 5: 기존 문서 편집

```bash
source "$VENV"

# 1. HWPX → 디렉토리
python3 "$SKILL_DIR/scripts/office/unpack.py" document.hwpx ./unpacked/

# 2. XML 직접 편집
#    본문: ./unpacked/Contents/section0.xml
#    스타일: ./unpacked/Contents/header.xml

# 3. 다시 HWPX로 패키징
python3 "$SKILL_DIR/scripts/office/pack.py" ./unpacked/ edited.hwpx

# 4. 검증
python3 "$SKILL_DIR/scripts/validate.py" edited.hwpx
```

---

## 워크플로우 6: 읽기/텍스트 추출

```bash
source "$VENV"

python3 "$SKILL_DIR/scripts/text_extract.py" document.hwpx
python3 "$SKILL_DIR/scripts/text_extract.py" document.hwpx --include-tables
python3 "$SKILL_DIR/scripts/text_extract.py" document.hwpx --format markdown
```

---

## 워크플로우 7: 레퍼런스 기반 문서 생성

```bash
source "$VENV"

# 1. 심층 분석
python3 "$SKILL_DIR/scripts/analyze_template.py" reference.hwpx

# 2. header.xml, section0.xml 추출
python3 "$SKILL_DIR/scripts/analyze_template.py" reference.hwpx \
  --extract-header /tmp/ref_header.xml \
  --extract-section /tmp/ref_section.xml

# 3. 추출한 header.xml + 새 section0.xml로 빌드
python3 "$SKILL_DIR/scripts/build_hwpx.py" \
  --header /tmp/ref_header.xml \
  --section /tmp/new_section0.xml \
  --output result.hwpx

# 4. 검증
python3 "$SKILL_DIR/scripts/validate.py" result.hwpx
```

---

## section0.xml 작성 가이드

### 필수 구조

첫 문단의 첫 run에 반드시 `<hp:secPr>` + `<hp:colPr>` 포함. 각 템플릿의 section0.xml 첫 문단을 그대로 복사하면 된다.

### 문단

```xml
<hp:p id="고유ID" paraPrIDRef="문단스타일ID" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="글자스타일ID">
    <hp:t>텍스트 내용</hp:t>
  </hp:run>
</hp:p>
```

### 빈 줄

```xml
<hp:p id="고유ID" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0"><hp:t/></hp:run>
</hp:p>
```

### 실전 패턴: section0.xml 인라인 작성

```bash
SECTION=$(mktemp /tmp/section0_XXXX.xml)
cat > "$SECTION" << 'XMLEOF'
<?xml version='1.0' encoding='UTF-8'?>
<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">
  <!-- secPr 문단은 templates/gonmun/section0.xml에서 복사 -->
  <!-- ... -->
</hs:sec>
XMLEOF

python3 "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun --section "$SECTION" --output result.hwpx
rm -f "$SECTION"
```

### 표 크기 계산

- **A4 본문폭**: 42520 HWPUNIT = 59528(용지) - 8504×2(좌우여백)
- **열 너비 합 = 본문폭** (42520 또는 결재표: 22680)
- 예: 2열 (라벨:내용 = 1:4) → 8504 + 34016 = 42520
- **행 높이**: 셀당 보통 1600~4000 HWPUNIT

### ID 규칙

- 문단 id: `1000000001`부터 순차 증가
- 표 id: `1000000098`~`1000000099` 등 별도 범위
- 테이블 내부 문단: `1000000050`~`1000000070` 범위
- 모든 id는 문서 내 고유해야 함

---

## 템플릿별 스타일 ID 맵

### gonmun (공문)

| ID | 유형 | 설명 |
|----|------|------|
| charPr 0 | 글자 | 10pt 함초롬바탕, 기본 |
| charPr 7 | 글자 | 22pt 볼드 함초롬바탕 (기관명) |
| charPr 8 | 글자 | 16pt 볼드 함초롬바탕 (서명자) |
| charPr 9 | 글자 | 8pt 함초롬바탕 (하단 연락처) |
| charPr 10 | 글자 | 10pt 볼드 함초롬바탕 (표 헤더) |
| paraPr 0 | 문단 | JUSTIFY, 160% 줄간격 |
| paraPr 20 | 문단 | CENTER, 160% 줄간격 |
| paraPr 21 | 문단 | CENTER, 130% (표 셀) |
| paraPr 22 | 문단 | JUSTIFY, 130% (표 셀) |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #D6DCE4 배경 |

### report (업무보고서) — 업무보고서 서식 기반

| ID | 유형 | 설명 |
|----|------|------|
| charPr 5 | 글자 | HY헤드라인M (제목 영역) |
| charPr 7 | 글자 | 섹션 기호 (󰏚) |
| charPr 8 | 글자 | HY헤드라인M 16pt (섹션 제목) |
| charPr 9 | 글자 | 휴먼명조 15pt (❍ 본문) |
| charPr 10 | 글자 | 중고딕 13pt (※ 비고) |
| charPr 11 | 글자 | 보조 텍스트 |
| charPr 13 | 글자 | 기본 텍스트 |
| paraPr 12 | 문단 | 기본 (제목/구분선 포함) |
| paraPr 13 | 문단 | 빈 줄 |
| paraPr 14 | 문단 | 구분 |
| paraPr 15 | 문단 | 제목 하단 |
| paraPr 16 | 문단 | 섹션 제목 (번호 붙임) |
| paraPr 17 | 문단 | 본문 (들여쓰기) |
| paraPr 18 | 문단 | secPr 문단 |
| paraPr 19 | 문단 | 머리글 하단 |

### minutes (회의록)

| ID | 유형 | 설명 |
|----|------|------|
| charPr 7 | 글자 | 18pt 볼드 (제목) |
| charPr 8 | 글자 | 12pt 볼드 (섹션 라벨) |
| charPr 9 | 글자 | 10pt 볼드 (표 헤더) |
| paraPr 20 | 문단 | CENTER, 160% |
| paraPr 21 | 문단 | CENTER, 130% (표 셀) |
| paraPr 22 | 문단 | JUSTIFY, 130% (표 셀) |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #E2EFDA 배경 |

### draft (기안문) — gonmun + 결재라인 추가

| ID | 유형 | 설명 |
|----|------|------|
| charPr 7 | 글자 | 22pt 볼드 함초롬바탕 (기관명) |
| charPr 8 | 글자 | 16pt 볼드 함초롬바탕 (서명자) |
| charPr 9 | 글자 | 8pt 함초롬바탕 (하단 연락처) |
| charPr 10 | 글자 | 10pt 볼드 함초롬바탕 (표 헤더) |
| charPr 11 | 글자 | 9pt 함초롬바탕 (결재란 직위) |
| charPr 12 | 글자 | 10pt 함초롬바탕 (결재란 성명) |
| paraPr 20 | 문단 | CENTER, 160% 줄간격 |
| paraPr 21 | 문단 | CENTER, 130% (표 셀) |
| paraPr 22 | 문단 | JUSTIFY, 130% (표 셀) |
| paraPr 23 | 문단 | CENTER, 100% (결재란 셀) |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #D6DCE4 배경 |
| borderFill 5 | 테두리 | SOLID 0.12mm + #E7E7E7 배경 (결재란 직위) |
| borderFill 6 | 테두리 | SOLID 0.12mm, 배경 없음 (결재란 서명/성명) |

---

## 플레이스홀더 vs 하드코딩 정보

### 하드코딩 (템플릿에 고정)

| 항목 | 위치 | 값 |
|------|------|-----|
| 기관명 | gonmun/draft Para 3(5), report Para 3, minutes Para 3 | 울산광역시교육청 |
| 주소/우편번호/홈페이지 | gonmun/draft 하단 시행정보 | 우 44540 / 울산광역시 중구... / www.use.go.kr |

### 플레이스홀더 (사용자가 대체)

| 플레이스홀더 | 사용 템플릿 | 설명 |
|-------------|------------|------|
| {{수신자}} | gonmun, draft | 수신 기관/부서 |
| {{경유}} | gonmun, draft | 경유 부서 |
| {{제목}} | gonmun, draft | 문서 제목 |
| {{본문1}}, {{본문2}} | gonmun, draft | 본문 내용 |
| {{표 또는 상세내용}} | gonmun, draft | 표 또는 상세내용 |
| {{직위 성명}} | gonmun, draft | 서명자 직위와 성명 |
| {{시행번호}} | gonmun, draft | 시행 문서번호 |
| {{시행일자}} | gonmun, draft | 시행 날짜 |
| {{전화번호}} | gonmun, draft | 연락처 전화 |
| {{팩스번호}} | gonmun, draft | 팩스 번호 |
| {{이메일}} | gonmun, draft | 이메일 주소 |
| {{작성일}} | report | 보고 날짜 (예: 2026. 3. 2.(월)) |
| {{부서}} | report | 작성 부서 |
| {{직위}} | report | 작성자 직위 |
| {{작성자}} | report | 작성자 성명 |
| {{연락처}} | report | 연락처 전화번호 |
| {{섹션1 제목}}, {{섹션2 제목}} | report | 각 섹션 제목 |
| {{본문 내용}} | report | 본문 (2회 사용, 동일 값 치환) |
| {{세부 내용}} | report | 세부 사항 |
| {{비고}} | report | 참고/비고 |
| {{표 제목}} | report | 표 앞 설명 |
| {{회의록 제목}} | minutes | 회의 제목 |
| {{YYYY년 MM월 DD일 HH:MM}} | minutes | 회의 일시 |
| {{장소}} | minutes | 회의 장소 |
| {{참석자 목록}} | minutes | 참석자 |
| {{작성자}} | minutes | 작성자 |
| {{안건 내용}} | minutes | 안건 |
| {{논의 내용}} | minutes | 논의 사항 |
| {{결정 사항}} | minutes | 결정된 사항 |
| {{향후 조치 사항}} | minutes | 향후 계획 |
| {{담당자명}} | draft | 결재란 담당자 |
| {{팀장명}} | draft | 결재란 팀장 |
| {{과장명}} | draft | 결재란 과장 |
| {{국장명}} | draft | 결재란 국장 |
| {{일자}} | draft | 결재 일자 |

---

## 스크립트 요약

| 스크립트 | 용도 |
|----------|------|
| `scripts/build_hwpx.py` | **핵심** — 템플릿 + XML → HWPX 조립 (BinData/content.hpf 자동 오버레이) |
| `scripts/analyze_template.py` | HWPX 심층 분석 (레퍼런스 기반 생성) |
| `scripts/office/unpack.py` | HWPX → 디렉토리 (XML pretty-print) |
| `scripts/office/pack.py` | 디렉토리 → HWPX (mimetype first) |
| `scripts/validate.py` | HWPX 파일 구조 검증 |
| `scripts/text_extract.py` | HWPX 텍스트 추출 (lxml 기반, hwpx 패키지 불필요) |

## 단위 변환

| 값 | HWPUNIT | 의미 |
|----|---------|------|
| 1pt | 100 | 기본 단위 |
| 10pt | 1000 | 기본 글자크기 |
| 1mm | 283.5 | 밀리미터 |
| A4 폭 | 59528 | 210mm |
| A4 높이 | 84188 | 297mm |
| 좌우여백 (gonmun/minutes/draft) | 8504 | 30mm |
| 본문폭 (gonmun/minutes/draft) | 42520 | 150mm |
| 좌우여백 (report) | 5669 | 20mm |
| 상하여백 (report) | 2834 | 10mm |
| 본문폭 (report) | 48190 | 170mm |

## Critical Rules

1. **HWPX만 지원**: `.hwp`(바이너리)는 지원 불가. 한글에서 `.hwpx`로 다시 저장 안내
2. **secPr 필수**: section0.xml 첫 문단의 첫 run에 secPr + colPr 반드시 포함
3. **mimetype 순서**: HWPX 패키징 시 mimetype은 첫 번째 ZIP 엔트리, ZIP_STORED
4. **네임스페이스 보존**: `hp:`, `hs:`, `hh:`, `hc:` 접두사 유지
5. **itemCnt 정합성**: header.xml의 charProperties/paraProperties/borderFills itemCnt = 실제 자식 수
6. **ID 참조 정합성**: section0.xml의 charPrIDRef/paraPrIDRef가 header.xml 정의와 일치
7. **기관 정보 변경 금지**: 하드코딩된 울산광역시교육청 정보는 수정하지 않음
8. **venv 사용**: `.venv/bin/python3` (lxml 자동 설치됨)
9. **검증 필수**: 생성 후 반드시 `validate.py`로 무결성 확인
10. **레퍼런스**: 상세 XML 구조는 `$SKILL_DIR/references/hwpx-format.md` 참조
11. **build_hwpx.py 우선**: 새 문서 생성은 build_hwpx.py 사용 (python-hwpx API 직접 호출 지양)
12. **빈 줄**: `<hp:t/>` 사용 (self-closing tag)
