# 오프라인 실제 데이터 fixture

- 출처: [한국체육산업개발주식회사_일산스포츠센터 강좌정보](https://www.data.go.kr/data/15114776/fileData.do), ID `15114776`
- 원본 로컬 파일: `/tmp/kspo_ilsan.csv` (전체 파일은 저장소에 포함하지 않음)
- 원본 SHA-256: `8efa60a38394ca4db23819000b71eeb6a06d0252ab6a28f4761e2164d00d719d`
- 추출: CP949, `csv.DictReader`로 읽고 `시작월`이 `2026-10`으로 시작하는 **157행 전부**를 동일한 필드·값으로 `csv.DictWriter`에 기록
- fixture: `ilsan_2026-10.csv`, CP949, 27,597바이트. 임의 생성한 강좌·요금 없음
- 정규화 결과: 155강좌. 원본의 `14:00~14:00` 2행은 그대로 포함하며 수집기가 시간 오류로 제외
- `정원`, 날짜 열, 강습반과 링크를 포함해 원본 필드를 유지. fixture의 해시는 수집 시 별도 계산하므로 전체 파일 해시와 다름
- 이용허락: 위 원 제공처의 이용허락범위 확인 필요. CSV만으로 별도 라이선스 유형을 추정하지 않음

재추출 예시(전체 파일의 위치만 로컬 환경에 맞게 수정):

```python
import csv
from pathlib import Path

with Path('/tmp/kspo_ilsan.csv').open(encoding='cp949', newline='') as source:
    reader = csv.DictReader(source)
    fields = reader.fieldnames
    rows = [row for row in reader if row['시작월'].startswith('2026-10')]
with Path('data/fixtures/ilsan_2026-10.csv').open('w', encoding='cp949', newline='') as target:
    writer = csv.DictWriter(target, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
```
