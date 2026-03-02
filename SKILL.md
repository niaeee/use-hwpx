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
│   ├── build_hwpx.py                      # 템플릿 + XML → .hwpx 조립 (핵심, --replace-title 지원)
│   ├── edit_section.py                    # section0.xml 문자열 기반 안전 편집 (lxml 금지)
│   ├── add_table.py                       # 표 안전 삽입 (header.xml 스타일 자동 추가)
│   ├── add_style.py                       # header.xml 스타일 안전 추가 (itemCnt 자동 갱신)
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
  --replace "섹션1 제목=추진 배경" --replace "본문 내용1=교육환경 개선 사업 추진" \
  --replace "세부 내용=노후 교실 리모델링" --replace "비고=예산 확보 완료" \
  --replace "섹션2 제목=추진 계획" --replace "본문 내용2=교육시설 현대화 추진" \
  --replace "표 제목=세부 추진 일정" \
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
| 7 | 17 | 9 | ❍ {{본문 내용1}} (휴먼명조 15pt) |
| 8 | 17 | 9 | - {{세부 내용}} (휴먼명조 15pt) |
| 9 | 17 | 10 | ※ {{비고}} (중고딕 13pt) |
| 10 | 17 | 7/8 | 󰏚 {{섹션2 제목}} (HY헤드라인M 16pt) |
| 11 | 17 | 9 | ❍ {{본문 내용2}} (휴먼명조 15pt) |
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

- **글꼴**: 맑은 고딕 10pt, 자간 -5%, 장평 100%
- **표 너비**: 본문폭(48190) 이내, 샘플 표는 3열×3행 (열너비 12120×3 = 36360)
- **셀 여백**: left/right 425 (1.5mm), top/bottom 142 (0.5mm)
- **테두리**: 바깥 0.4mm, 안쪽 0.12mm, 헤더 하단 0.4mm
- **헤더 배경**: #DCDCDC (연회색), 굵게(Bold)
- **줄 간격**: 130% (본문보다 좁게)

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
| {{본문 내용1}}, {{본문 내용2}} | report | 본문 (섹션별 개별 치환) |
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
| `scripts/build_hwpx.py` | **핵심** — 템플릿 + XML → HWPX 조립 (BinData/content.hpf 자동 오버레이, `--replace-title` 지원) |
| `scripts/edit_section.py` | section0.xml 문자열 기반 안전 편집 (drawText 포함, lxml 사용 금지) |
| `scripts/add_table.py` | section0.xml에 HWPX 표 안전 삽입 (header.xml 스타일 자동 추가) |
| `scripts/add_style.py` | header.xml에 charPr/paraPr/borderFill/font 안전 추가 (itemCnt 자동 갱신) |
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
13. **lxml로 section0.xml 파싱 금지**: lxml은 footer, tbl, header 등 원본 XML 구조를 파괴한다. 반드시 **문자열 기반(str.replace, re.sub)** 방식으로 편집하거나 `edit_section.py` 사용
14. **report 제목은 drawText 내부**: report 템플릿의 제목은 일반 `<hp:t>` 문단이 아니라 drawText 도형 내부에 있음. `--replace-title` 옵션 또는 `edit_section.py --replace-title` 사용
15. **linesegarray 제거 필수**: `--replace`로 텍스트 길이가 변경되면 `<hp:linesegarray>` 레이아웃 캐시가 무효화되어 글자 겹침 발생. `build_hwpx.py`는 `--replace` 후 자동 제거. 수동 편집 시에도 반드시 제거할 것
16. **표 treatAsChar="0"**: 표의 `<hp:pos treatAsChar="0">`을 사용. `treatAsChar="1"`(인라인)은 앞 문단과 같은 줄에 배치되어 여백이 비정상적으로 넓어지는 문제 발생
17. **앵커 텍스트 고유성**: 동일 텍스트가 여러 곳에 있으면 의도와 다른 위치에 삽입됨. 다중 매치 시 `--after-nth N`으로 N번째 매치 지정. 짧은 부분문자열(예: "계획") 대신 고유한 전체 문구 사용
18. **add_table.py 앵커 필수**: 앵커 텍스트를 찾지 못하면 ERROR로 중단. 문서 끝 삽입이 의도적이면 `--fallback-append` 명시
19. **report footer 구조 보존**: report section0.xml의 footer는 `<hp:p>` 내부 `<hp:ctrl><hp:footer>` 구조. footer가 포함된 문단을 삭제하면 XML 깨짐. footer 문단은 절대 삭제/이동 금지

---

## Anti-patterns (절대 하면 안 되는 것)

### 1. lxml로 section0.xml을 파싱하지 마라
- lxml 파싱은 footer, tbl, header 등 원본 XML 구조를 파괴한다
- report 템플릿 원본: `tbl 2개, footer 2개, header 12개` → lxml 파싱 후: `tbl 0개, footer 0개` → 구조 깨짐
- 반드시 **문자열 기반(str.replace, re.sub)** 방식으로 편집
- 복잡한 편집이 필요하면 `edit_section.py` 사용

### 2. charPr 복사 시 regex로 속성값을 일괄 치환하지 마라
- `re.sub(r'hangul="\d+"', 'hangul="6"', block)` 같은 패턴은 fontRef뿐 아니라 ratio, spacing, relSz의 값까지 변경한다
- ratio=6 (6%)이 되어 글자가 안 보이는 치명적 버그 발생
- charPr을 새로 만들 때는 **전체 XML을 명시적으로 작성**하거나 `add_style.py` 사용

### 3. 표 셀에서 paraPrIDRef="0"을 사용하지 마라
- paraPr 0은 문서의 기본 스타일로, 한글 프로그램이 기본 폰트를 우선 적용할 수 있다
- 표 전용 paraPr을 별도로 생성하여 사용 (`add_table.py`가 자동 처리)

### 4. 특수기호를 \uXXXX로 입력하지 마라 (Supplementary PUA 문자)
- report 섹션 기호(󰏚)는 **U+F03DA** (4바이트, Supplementary PUA-B)
- Python에서 `\uF3DA`는 **U+F3DA** (3바이트, BMP PUA) → **다른 문자!**
- 반드시 `\U000F03DA` (대문자 U + 8자리) 사용

```python
wrong = '\uF3DA'      # U+F3DA (3바이트, BMP PUA) ← 깨짐!
correct = '\U000F03DA'  # U+F03DA (4바이트, Supplementary PUA-B) ← 정상
```

### 5. 폰트명의 띄어쓰기를 무시하지 마라
- "맑은고딕" ≠ "맑은 고딕" — 한글 프로그램은 정확한 이름만 인식
- `add_style.py`의 폰트명 검증 기능 활용

### 6. header.xml의 itemCnt를 수동으로 관리하지 마라
- charProperties, paraProperties, borderFills의 itemCnt는 실제 자식 요소 수와 반드시 일치해야 함
- `add_style.py`가 자동 갱신

### 7. report 템플릿의 secPr/머리글/footer 구조를 누락하지 마라
### 8. linesegarray를 남겨두지 마라
- `<hp:linesegarray>`는 한글이 저장 시 생성하는 **문자별 위치 레이아웃 캐시**
- `--replace`로 텍스트 길이가 바뀌면 이 캐시가 원래 길이 기준이라 **글자가 겹치거나 잘림**
- `build_hwpx.py`는 `--replace` 후 자동으로 제거 (`re.sub`으로 전체 블록 삭제)
- 수동으로 section0.xml을 편집한 경우에도 반드시 제거:
```python
content = re.sub(r'\s*<hp:linesegarray>.*?</hp:linesegarray>', '', content, flags=re.DOTALL)
```
- 한글 프로그램은 linesegarray가 없으면 열 때 자동 재계산하므로 삭제해도 안전

### 10. 짧은 앵커 텍스트를 사용하지 마라
- "계획", "현황" 같은 짧은 단어는 문서 내 여러 곳에 존재할 수 있어 의도와 다른 위치에 삽입됨
- 전체 문구(예: "연도별 추진 일정", "추진 배경") 사용. 다중 매치 시 `--after-nth N` 활용

### 11. add_table.py 앵커 에러를 무시하지 마라
- 앵커 미발견 시 ERROR로 중단됨 (이전에는 WARNING+문서 끝 삽입이었으나 수정됨)
- 의도적 문서 끝 삽입은 `--fallback-append` 또는 `--append` 사용

### 9. 앵커 텍스트가 표 안에도 있을 수 있다 — 표 밖 매치만 사용하라
- `insert_after_anchor("세부 추진 일정", ...)` 호출 시, 해당 텍스트가 표 셀 안에도 존재할 수 있음
- 표 내부 `<hp:tbl>...<hp:t>세부 추진 일정</hp:t>...</hp:tbl>` 위치에 삽입하면 표 구조가 깨짐
- `edit_section.py`와 `add_table.py`는 `_find_anchor_outside_table()`로 표 밖 매치만 사용
- 직접 `content.find()`를 쓸 때도 반드시 해당 위치가 `<hp:tbl>` 내부인지 확인
- report 템플릿의 section0.xml에는 secPr 문단, 머리글 이미지(container+rect+pic), 헤더/푸터 5개, drawText 도형 등 복잡한 구조가 있다
- 커스텀 section0.xml 사용 시 원본의 앞부분(secPr~로고)과 뒷부분(footer)을 반드시 보존
- 가장 안전한 방법: 기본 빌드 → unpack → 문자열 편집 → repack

---

## 폰트 이름 정확한 표기

한글 프로그램은 정확한 폰트 이름만 인식한다. 띄어쓰기 오류 시 다른 폰트로 fallback된다.

| 올바른 이름 | 흔한 실수 | 비고 |
|------------|----------|------|
| 맑은 고딕 | 맑은고딕 | 띄어쓰기 필수 |
| 함초롬돋움 | 함초롬 돋움 | 붙여쓰기 |
| 함초롬바탕 | 함초롬 바탕 | 붙여쓰기 |
| HY헤드라인M | HY 헤드라인M | 붙여쓰기 |
| 휴먼명조 | 휴먼 명조 | 붙여쓰기 |
| 한양중고딕 | 한양 중고딕 | 붙여쓰기 |
| 양재 소슬 | 양재소슬 | 띄어쓰기 필수 |

---

## report 템플릿 drawText 제목 구조

report 템플릿의 제목은 drawText 도형 내부에 하드코딩되어 있다. 일반 `{{}}` 플레이스홀더와 달리, drawText 내부 텍스트를 교체하려면 특별한 처리가 필요하다.

### drawText 구조
```
container (묶음 개체)
  └─ rect (사각형 도형)
      └─ drawText
          └─ subList
              └─ hp:p
                  └─ hp:run charPrIDRef="5"
                      └─ hp:t → "HY헤드라인M" (기본 제목 텍스트)
  └─ pic (로고 이미지, image2)
```

### 제목 교체 방법

**방법 1: build_hwpx.py --replace-title** (권장)
```bash
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report \
  --replace-title "AI 활용 업무보고" \
  --replace "작성일=2026. 3. 2.(월)" \
  --output report.hwpx
```

**방법 2: edit_section.py --replace-title** (unpack 후)
```bash
python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --replace-title "AI 활용 업무보고"
```

**방법 3: 직접 문자열 치환** (코드 내)
```python
content = content.replace("HY헤드라인M", "AI 활용 업무보고")
# 주의: 이 경우 header.xml의 폰트 이름까지 바뀌지 않도록 section0.xml에서만 실행
```

---

## 워크플로우 8: report에 표 삽입 (고급)

기본 빌드 → unpack → 스타일 추가 → 표 삽입 → repack의 전체 과정.

```bash
source "$VENV"

# 1. 기본 report 빌드
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report \
  --replace "작성일=2026. 3. 2.(월)" --replace "부서=교육혁신과" \
  --replace "직위=주무관" --replace "작성자=홍길동" --replace "연락처=1234" \
  --replace "섹션1 제목=추진 배경" --replace "본문 내용1=AI 활용 교육 추진" \
  --replace "세부 내용=교실 수업 적용" --replace "비고=예산 확보 완료" \
  --replace "섹션2 제목=추진 계획" --replace "본문 내용2=세부 추진 사항" \
  --replace "표 제목=세부 추진 일정" \
  --replace-title "AI 활용 업무보고" \
  --title "AI 활용 업무보고" --creator "교육혁신과" --output report.hwpx

# 2. unpack
python3 "$SKILL_DIR/scripts/office/unpack.py" report.hwpx ./unpacked/

# 3. 표 데이터 준비
cat > /tmp/table_data.json << 'EOF'
{
  "columns": ["분류", "항목", "2024년", "2025년", "2026년"],
  "col_widths": [4819, 8674, 11566, 12529, 10602],
  "rows": [
    {"data": ["교수학습", "우리아이(AI)", "개발착수", "정식운영", "전교운영"], "category_span": 2},
    {"data": ["", "미래교사단", "101명선발", "콘텐츠개발", "고도화"]},
    {"data": ["행정지원", "자동화시스템", "도입검토", "시범운영", "전면확대"], "category_span": 1}
  ]
}
EOF

# 4. 표 삽입 (header.xml 스타일 자동 추가 + section0.xml에 표 삽입)
python3 "$SKILL_DIR/scripts/add_table.py" ./unpacked/ \
  --data /tmp/table_data.json \
  --insert-after "세부 추진 일정" \
  --font "맑은 고딕" --font-size 10 \
  --header-bg "#DCDCDC" --body-width 48190

# 5. repack
python3 "$SKILL_DIR/scripts/office/pack.py" ./unpacked/ report_with_table.hwpx

# 6. 검증
python3 "$SKILL_DIR/scripts/validate.py" report_with_table.hwpx

# 정리
rm -rf ./unpacked/ /tmp/table_data.json
```

---

## 표 삽입 가이드 (report 템플릿)

### 표 삽입 워크플로우 (권장)

1. `build_hwpx.py`로 기본 report 빌드 (플레이스홀더 치환 포함)
2. `unpack.py`로 디렉토리 해제
3. `add_table.py`로 표 삽입 (header.xml 스타일 자동 추가 + section0.xml에 표 삽입)
4. `pack.py`로 리패키징
5. `validate.py`로 검증

### 표 XML 구조 (hp:tbl)

표를 포함하는 문단:
```xml
<hp:p paraPrIDRef="표전용paraPr" ...>
  <hp:run charPrIDRef="표용charPr">
    <hp:tbl ...>...</hp:tbl>
    <hp:t/>
  </hp:run>
</hp:p>
```

필수 속성:
- `treatAsChar="0"` (독립 배치, **"1"이면 앞 문단과 같은 줄에 배치되어 여백 이상**)
- `pageBreak="CELL"`
- `repeatHeader="1"` (페이지 넘김 시 헤더 반복)
- 표 너비 = 본문폭 (report: 48190, gonmun: 42520)

### 셀 구조
```xml
<hp:tc borderFillIDRef="3 또는 8" ...>
  <hp:subList vertAlign="CENTER" ...>
    <hp:p paraPrIDRef="표전용paraPr" ...>
      <hp:run charPrIDRef="표용charPr">
        <hp:t>텍스트</hp:t>
      </hp:run>
    </hp:p>
  </hp:subList>
  <hp:cellAddr colAddr="열" rowAddr="행"/>
  <hp:cellSpan colSpan="1" rowSpan="1"/>
  <hp:cellSz width="열폭" height="1000"/>
  <hp:cellMargin left="510" right="510" top="141" bottom="141"/>
</hp:tc>
```

### rowSpan 병합
- 병합 시작 셀: `rowSpan="N"` (N=병합 행 수)
- 병합된 행의 해당 열: `<hp:tc>` 자체를 생략 (출력하지 않음)

### 관공서 표 정렬 표준

| 영역 | 정렬 | 근거 |
|------|------|------|
| 헤더행 (분류/항목/연도) | 가운데 정렬 + 볼드 + 배경색 | 행정업무운영편람 |
| 분류 열 (카테고리) | 가운데 정렬 | 관공서 관행 |
| 항목 열 | 가운데 정렬 | 관공서 관행 |
| 내용 셀 (텍스트) | 왼쪽 정렬 | 가독성 |
| 숫자/금액 | 오른쪽 정렬 | 숫자 정렬 관행 |
| 셀 수직 정렬 | 가운데 (`vertAlign="CENTER"`) | 기본 |

### header.xml 수정 시 주의사항

1. **새 charPr 생성 시**: 전체 XML을 명시적으로 작성. regex로 fontRef만 바꾸면 ratio/spacing/relSz까지 변경됨
2. **borderFill 추가 시**: `<hc:fillBrush>` 태그로 배경색 지정. fillBrush 없으면 투명 배경
3. **fontface 등록 시**: 7개 언어 카테고리(HANGUL~USER) 모두에 동일 ID로 추가 + fontCnt 갱신
4. **itemCnt 갱신 필수**: charProperties, paraProperties, borderFills의 itemCnt를 실제 자식 수와 일치시켜야 함
5. 위 모든 작업은 `add_style.py`가 자동 처리

### 표 전용 글자 서식

표 안은 본문(휴먼명조 15pt)보다 작게 설정하여 시각적 구분 확보:

| 항목 | 값 | HWPUNIT |
|------|-----|---------|
| 폰트 | 맑은 고딕 | — |
| 크기 | 10pt (밀도 높으면 9pt 가능) | 1000 (900) |
| 자간 | -5% | spacing=-5 |
| 장평 | 100% | ratio=100 |
| 헤더 행 | 굵게(Bold) + 가운데 정렬 | — |
| 내용 행 | 왼쪽 정렬 (숫자/금액은 오른쪽) | — |
| 줄 간격 | 130% (본문보다 좁게) | — |

### 표 셀 여백

| 항목 | mm | HWPUNIT |
|------|-----|---------|
| 셀 왼쪽 | 1.5mm | 425 |
| 셀 오른쪽 | 1.5mm | 425 |
| 셀 위쪽 | 0.5mm | 142 |
| 셀 아래쪽 | 0.5mm | 142 |
| 셀 높이(1줄) | 10~12mm | 2835~3402 |

### 표 테두리 스타일

| 위치 | 두께 | 용도 |
|------|------|------|
| 바깥 테두리 | 실선 0.4mm (굵게) | 표 외곽선 |
| 안쪽 세로 구분선 | 실선 0.12mm (얇게) | 열 구분 |
| 안쪽 가로 구분선 | 실선 0.12mm (얇게) | 행 구분 |
| 헤더 행 하단 | 실선 0.4mm (강조) | 헤더와 본문 구분 |

`add_table.py`는 셀 위치에 따라 자동으로 적절한 borderFill을 생성하여 바깥/안쪽/헤더 하단 테두리를 구분 처리한다.

### 헤더 행 배경색

- 배경: 연회색 `#DCDCDC` (RGB 220, 220, 220)
- 글자: 검정, 굵게(Bold)

### 기타

- **표 너비**: 본문폭 이내 (report: 48190, gonmun: 42520)
- **표 전용 paraPr 사용**: paraPr 0 대신 표 전용 paraPr을 새로 만들어 기본 폰트 fallback 방지

### 열별 정렬 (col_aligns)

table_data.json에 `col_aligns`를 지정하면 열마다 개별 정렬 적용 (헤더 행 제외):

```json
{
  "columns": ["분류", "항목", "2024년", "2025년", "2026년"],
  "col_aligns": ["CENTER", "CENTER", "LEFT", "LEFT", "LEFT"],
  "rows": [...]
}
```

- `col_aligns` 지정 시 해당 열의 body 셀은 `category_align`/`item_align`/`content_align` 대신 `col_aligns[col]` 적용
- 헤더 행은 항상 `header_align` 적용 (보통 CENTER)
- `col_aligns` 미지정 시 기존 방식(category/item/content 기반) 동작
- 값: `"LEFT"`, `"CENTER"`, `"RIGHT"`

---

## report 다중 섹션 워크플로우

report 템플릿의 section0.xml에는 footer(꼬리말)가 포함되어 있다. 섹션을 추가할 때 footer와 섹션 내용이 엉키지 않도록 주의해야 한다.

### 기본 원칙

1. **section0.xml 하나에 모든 내용**: report 템플릿은 단일 `<hs:sec>` 안에 모든 내용이 들어간다
2. **footer는 `<hs:sec>` 닫기 직전**: footer/header 요소는 `</hs:sec>` 바로 앞에 위치
3. **새 내용은 footer 앞에 삽입**: `insert_before_closing_sec()` 또는 앵커 기반 삽입 사용
4. **표는 반드시 unpack → 삽입 → repack**: `add_table.py`가 header.xml 스타일을 추가해야 하므로

### 안전한 내용 추가 순서

```bash
# 1. 기본 빌드 (플레이스홀더 치환)
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report \
  --replace "섹션1 제목=추진 배경" --replace "섹션2 제목=추진 계획" \
  --replace-title "AI 활용 업무보고" \
  --output report.hwpx

# 2. unpack
python3 "$SKILL_DIR/scripts/office/unpack.py" report.hwpx ./unpacked/

# 3. 섹션 추가 (edit_section.py — 앵커 기반)
python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-section-title "향후 계획" --after "추진 계획"

python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-body "3월 중 시범운영 착수" --after "향후 계획"

# 4. 표 삽입 (필요 시)
python3 "$SKILL_DIR/scripts/add_table.py" ./unpacked/ \
  --data /tmp/table_data.json --insert-after "세부 추진 일정" \
  --body-width 48190

# 5. repack
python3 "$SKILL_DIR/scripts/office/pack.py" ./unpacked/ report_final.hwpx
```

### 주의사항

- `edit_section.py`의 앵커 검색은 표 내부 매치를 자동 건너뜀 (Anti-pattern #9)
- 플레이스홀더 치환 후 linesegarray가 자동 제거됨 (Critical Rule #15)
- 새 섹션 제목은 `make_section_title()`로 올바른 U+F03DA 기호 사용

---

## 관공서 문서 구조 가이드 (8-Section)

울산광역시교육청 업무보고서의 표준 구조. 모든 섹션이 필수는 아니며, 보고 내용에 따라 취사선택.

### 표준 8-섹션 구성

| 순서 | 섹션명 | 설명 | 필수 |
|------|--------|------|------|
| 1 | 추진 배경 | 사업/업무의 배경과 필요성 | O |
| 2 | 추진 근거 | 법적 근거, 상위 계획, 관련 규정 | △ |
| 3 | 현황 | 현재 상태, 통계, 실적 | O |
| 4 | 문제점/개선방향 | 현 체제의 문제점과 개선 방향 | △ |
| 5 | 추진 계획 | 세부 추진 사항, 일정 | O |
| 6 | 기대 효과 | 사업 추진으로 기대되는 성과 | △ |
| 7 | 행정 사항 | 예산, 인력, 유의사항 | △ |
| 8 | 향후 계획 | 향후 일정, 추진 로드맵 | O |

### 섹션별 작성 요령

**추진 배경**: 왜 이 업무를 추진하는지 간결하게 서술. 상위 기관 지시, 사회적 필요, 현장 요구 등.

**추진 근거**: 관련 법령, 교육부 지침, 교육청 계획 등을 명시. (예: "교육부 2026년 업무계획", "울산교육 미래비전 2030")

**현황**: 구체적 수치와 함께 현 상태 서술. 표를 활용하면 효과적.

**추진 계획**: 가장 중요한 섹션. 세부 사업별로 기간, 대상, 방법을 명시. 표 삽입 권장.

**기대 효과**: 정량적(수치) + 정성적(서술) 효과 병기.

**향후 계획**: 월별/분기별 추진 일정을 표로 정리.

### 작성 예시 (CLI)

```bash
# 6-섹션 보고서 (배경, 현황, 추진계획, 기대효과, 행정사항, 향후계획)
python3 "$SKILL_DIR/scripts/build_hwpx.py" --template report \
  --replace "섹션1 제목=추진 배경" \
  --replace "본문 내용1=AI 기반 맞춤형 교육 서비스 확대를 위한 기반 구축 필요" \
  --replace "세부 내용=교육부 '2026년 AI 디지털 교육 활성화 계획' 시행" \
  --replace "섹션2 제목=현황 및 추진 계획" \
  --replace "표 제목=연도별 추진 일정" \
  --replace-title "AI 디지털 교육 활성화 보고" \
  --output report.hwpx

# unpack 후 추가 섹션 삽입
python3 "$SKILL_DIR/scripts/office/unpack.py" report.hwpx ./unpacked/

python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-section-title "기대 효과" --after "연도별 추진 일정"
python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-body "AI 활용 수업 만족도 30% 향상" --after "기대 효과"
python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-body "교원 업무 부담 20% 경감" --after "AI 활용 수업 만족도"

python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-section-title "향후 계획" --after "교원 업무 부담"
python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-body "2026. 3. 시범학교 10교 선정 및 운영" --after "향후 계획"
python3 "$SKILL_DIR/scripts/edit_section.py" ./unpacked/ \
  --add-body "2026. 6. 중간 성과 분석 및 확대 방안 마련" --after "시범학교 10교"

python3 "$SKILL_DIR/scripts/office/pack.py" ./unpacked/ report_full.hwpx
```

---

## 문단 작성 규칙

### 핵심 원칙: 1문단 3줄 이내

관공서 보고서는 **간결한 문장**이 핵심. 한 문단(❍ 항목)은 **최대 3줄(약 120자)** 이내로 작성.

### 구체적 기준

| 항목 | 기준 | 비고 |
|------|------|------|
| 문단 길이 | 최대 3줄 (120자) | A4 170mm 기준, 15pt 휴먼명조 |
| 문장 수 | 1~2문장 | 3문장 이상 시 분리 |
| 세부 항목 | 하위 레벨로 분리 | ❍ → - → ※ 순으로 전개 |
| 표 활용 | 3항목 이상 나열은 표 사용 | 가독성 향상 |

### 예시

장문 → 구조화 분리:
```
❍ AI 기반 맞춤형 학습 플랫폼 전교 확대 추진
  - 2025년 시범운영 성과: 학습 성취도 15%↑, 교원 만족도 85%
  - 2026년 전체 학교 확대를 위한 예산 확보 및 시스템 고도화
  ※ 교육부 'AI 디지털 교과서 도입 사업' 연계 추진
```
