import os
import re
import datetime
from collections import Counter
import matplotlib.pyplot as plt

# 파일들이 위치한 폴더 경로 (예: 현재 폴더)
folder_path = '.'

# 파일 이름 패턴: capture_YYYYMMDD-HHMMSS.jpg
pattern = r'capture_(\d{8})-(\d{6})\.jpg'

# 폴더 내의 파일들을 리스트업
files = os.listdir(folder_path)

# 촬영 시간을 저장할 리스트
capture_times = []

for file in files:
    match = re.match(pattern, file)
    if match:
        date_str, time_str = match.groups()
        # 시간 문자열에서 시, 분, 초 추출
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        # datetime.time 객체로 저장
        capture_times.append(datetime.time(hour, minute, second))

# 분(minute) 단위로 촬영 건수 집계
minute_counts = Counter(time.minute for time in capture_times)

# 0분부터 59분까지의 건수를 리스트로 준비 (없는 분은 0)
minutes = list(range(60))
counts = [minute_counts.get(m, 0) for m in minutes]

# 막대그래프로 시각화
plt.figure(figsize=(12, 6))
bars = plt.bar(minutes, counts, color='skyblue')
plt.xlabel('분 (0~59)')
plt.ylabel('촬영 건수')
plt.title('분 단위 촬영 건수')
plt.xticks(minutes)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# 각 막대 위에 촬영 건수 표기
for bar in bars:
    height = bar.get_height()
    plt.annotate(f'{height}',
                 xy=(bar.get_x() + bar.get_width() / 2, height),
                 xytext=(0, 3),  # 텍스트와 막대 사이의 간격
                 textcoords="offset points",
                 ha='center', va='bottom')

plt.show()
